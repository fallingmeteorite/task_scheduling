# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Proxy Server Module

This module provides the main proxy server functionality that coordinates between
task managers, server managers, and network communications.

Key Features:
    - Client connection handling and message routing
    - Task distribution to available servers
    - Server health monitoring and management
    - Graceful shutdown and resource cleanup

Classes:
    ProxyServer: Main proxy server class coordinating all operations

Global Variables:
    proxy_server: Global proxy server instance
"""

import time
import socket
import threading
import signal

from typing import Dict
from task_scheduling.common import logger, config
from task_scheduling.proxy_server.utils import NetworkManager, ServerManager, TaskManager


class ProxyServer:
    """Main Proxy Server - Coordinates all managers"""

    def __init__(self):
        self.server_socket = None
        self.health_thread = None
        self.host = "localhost"
        self.port = config["proxy_ip"]
        self.running = False
        self.shutdown_event = threading.Event()

        # Initialize managers
        self.network = NetworkManager()
        self.tasks = TaskManager()
        self.servers = ServerManager()

        # Message handlers
        self.message_handlers = {
            'client_submit_task': self._handle_task_submission,
            'server_register': self._handle_server_register,
            'server_heartbeat': self._handle_heartbeat,
        }

        # Setup signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.debug(f"Received signal, gracefully shutting down server...")
        self.stop()

    def start(self):
        """Start the server"""
        if self.running:
            logger.warning("Server is already running")
            return

        self.running = True
        self.shutdown_event.clear()

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.server_socket.settimeout(1.0)

            logger.info(f"Proxy server started on {self.host}:{self.port}")

            # Start task dispatcher thread
            self.dispatcher_thread = threading.Thread(target=self._task_dispatcher_loop)
            self.dispatcher_thread.daemon = False
            self.dispatcher_thread.name = "TaskDispatcher"
            self.dispatcher_thread.start()

            # Start health check thread
            self.health_thread = threading.Thread(target=self._health_check_loop)
            self.health_thread.daemon = False
            self.health_thread.name = "HealthChecker"
            self.health_thread.start()

            logger.info("Server startup completed. Press Ctrl+C to stop the server.")

            # Main connection loop
            self._connection_loop()

        except Exception as e:
            logger.error(f"Server startup failed: {e}")
            self.stop()

    def _connection_loop(self):
        """Main connection handling loop"""
        while self.running and not self.shutdown_event.is_set():
            try:
                client_sock, addr = self.server_socket.accept()
                if self.shutdown_event.is_set():
                    client_sock.close()
                    break

                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr), daemon=True
                )
                client_thread.start()

            except socket.timeout:
                continue
            except OSError as e:
                if self.running and not self.shutdown_event.is_set():
                    logger.error(f"Connection acceptance error: {e}")
                break
            except Exception as e:
                if self.running and not self.shutdown_event.is_set():
                    logger.error(f"Unknown connection error: {e}")

    def _handle_client(self, sock: socket.socket, addr: tuple):
        """Handle client connection"""
        if self.shutdown_event.is_set():
            sock.close()
            return

        try:
            message = self.network.receive_message(sock)
            if message and 'type' in message and not self.shutdown_event.is_set():
                handler = self.message_handlers.get(message['type'])
                if handler:
                    handler(message, addr)
        except Exception as e:
            if not self.shutdown_event.is_set():
                logger.error(f"Error handling client {addr}: {e}")
        finally:
            sock.close()

    def _task_dispatcher_loop(self):
        """Task dispatcher main loop"""
        logger.debug("Task dispatcher started")
        empty_cycles = 0
        while self.running and not self.shutdown_event.is_set():
            try:
                task = self.tasks.get_pending_task()
                if task:
                    empty_cycles = 0
                    if self.shutdown_event.is_set():
                        self.tasks.requeue_task(task)
                        continue

                    server = self.servers.select_best_server()
                    if server:
                        success = self.network.send_to_server(server, {
                            'type': 'execute_task',
                            'task_data': task
                        })
                        if success:
                            task_id = task.get('task_id', 'unknown')
                            logger.debug(f"Task dispatched successfully: {task_id} -> Server {server['port']}")
                        else:
                            self.tasks.requeue_task(task)
                            self.servers.mark_server_inactive(server['port'])
                            logger.debug(f"Task dispatch failed, server {server['port']} marked as inactive")
                    else:
                        self.tasks.requeue_task(task)
                        if not self.shutdown_event.is_set():
                            logger.debug("No available servers, task requeued")
                            time.sleep(2)
                else:
                    empty_cycles += 1
                    if empty_cycles > 10:  # Extend sleep after 10 empty cycles
                        time.sleep(0.5)
                    else:
                        time.sleep(0.1)

            except Exception as e:
                if not self.shutdown_event.is_set():
                    logger.error(f"Task dispatcher error: {e}")
                time.sleep(0.1)

        logger.debug("Task dispatcher stopped")

    def _health_check_loop(self):
        """Regular health check loop"""
        logger.debug("Health checker started")

        while self.running and not self.shutdown_event.is_set():
            try:
                # Check if there are servers to monitor
                if not self.servers.servers:
                    logger.debug("No registered servers, waiting 30 seconds before rechecking...")
                    # Check shutdown event during wait
                    for _ in range(300):  # 30 seconds, checking every 0.1 seconds
                        if self.shutdown_event.is_set():
                            break
                        time.sleep(0.1)
                    continue

                logger.warning("Performing server health checks...")
                active_count = self.servers.health_check_all(self.network)
                logger.debug(f"Health check completed, active servers: {active_count}")

                # Adjust check interval based on active server count
                if active_count == 0:
                    check_interval = 10  # Check every 10 seconds if no active servers
                    logger.debug("No active servers, rechecking in 10 seconds")
                else:
                    check_interval = 30  # Check every 30 seconds with active servers
                    logger.debug(f"Active servers: {active_count}, next check in 30 seconds")

                # Interruptible wait
                for _ in range(check_interval * 10):
                    if self.shutdown_event.is_set():
                        break
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                # Wait 5 seconds on error
                for _ in range(50):
                    if self.shutdown_event.is_set():
                        break
                    time.sleep(0.1)

        logger.warning("Health checker stopped")

    def _check_server_health(self, server_port: int, host: str) -> bool:
        """Check server health status during registration"""
        try:
            logger.debug(f"Checking health of server {host}:{server_port} during registration...")

            # Send health check request
            server_info = {'host': host, 'port': server_port}
            success = self.network.send_to_server(server_info, {
                'type': 'health_check',
                'timestamp': time.time()
            })

            if success:
                logger.info(f"Server {host}:{server_port} passed initial health check")
                return True
            else:
                logger.warning(f"Server {host}:{server_port} failed initial health check")
                return False

        except Exception as e:
            logger.error(f"Health check error for server {host}:{server_port}: {e}")
            return False

    # Message handler functions
    def _handle_task_submission(self, message: Dict, addr: tuple):
        """Handle task submission from clients"""
        if self.shutdown_event.is_set():
            return

        task_data = message.get('task_data', {})

        # Validate task data
        if not self.tasks.validate_task_data(task_data):
            logger.error(f"Task data validation failed from {addr}")
            return

        task_id = self.tasks.submit_task(task_data)
        if task_id:
            logger.debug(f"Received task from {addr}: {task_data['task_name']} (ID: {task_id})")

    def _handle_server_register(self, message: Dict, addr: tuple):
        """Handle server registration with initial health check"""
        if self.shutdown_event.is_set():
            return

        server_port = message.get('server_port')
        if server_port:
            host = message.get('host', addr[0])

            # Check if already registered
            if server_port in self.servers.servers:
                # Update heartbeat for existing server
                self.servers.update_heartbeat(server_port)
                logger.debug(f"Server {host}:{server_port} heartbeat updated")
            else:
                # Perform health check for new server registration
                logger.info(f"New server registration attempt: {host}:{server_port}")

                if self._check_server_health(server_port, host):
                    # Health check passed, register the server
                    self.servers.register_server(server_port, host, addr)
                    logger.info(f"Server {host}:{server_port} registered successfully")
                else:
                    # Health check failed, log warning
                    logger.warning(f"Server {host}:{server_port} registration rejected due to health check failure")

    def _handle_heartbeat(self, message: Dict, addr: tuple):
        """Handle heartbeat messages from servers"""
        if self.shutdown_event.is_set():
            return

        server_port = message.get('server_port')
        if server_port in self.servers.servers:
            self.servers.update_heartbeat(server_port)
            logger.debug(f"Server {server_port} heartbeat received")

    def stop(self):
        """Stop server - graceful shutdown"""
        if not self.running:
            return

        logger.warning("Starting server shutdown...")
        self.running = False
        self.shutdown_event.set()

        # Close server socket
        if hasattr(self, 'server_socket'):
            self.server_socket.close()

        # Wait for threads to finish (with timeout)
        threads_to_wait = []
        if hasattr(self, 'dispatcher_thread') and self.dispatcher_thread.is_alive():
            threads_to_wait.append(self.dispatcher_thread)
        if hasattr(self, 'health_thread') and self.health_thread.is_alive():
            threads_to_wait.append(self.health_thread)

        # Wait for threads to finish
        for thread in threads_to_wait:
            if thread.is_alive():
                thread.join(timeout=0.1)
                logger.warning(f"Warning: {thread.name} thread did not finish within timeout")

        logger.warning(f"Server stopped")

    def wait_for_shutdown(self):
        """Wait for server to fully shutdown"""
        if hasattr(self, 'dispatcher_thread'):
            self.dispatcher_thread.join(timeout=0.1)
        if hasattr(self, 'health_thread'):
            self.health_thread.join(timeout=0.1)


# Global instance and exit handling
proxy_server = ProxyServer()
