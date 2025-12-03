# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Proxy Server Module - Integrated Version
Simplified version with reduced log output
"""

import time
import socket
import threading
import signal

from typing import Dict, Any, Optional, List
from task_scheduling.common import logger, config
from task_scheduling.proxy_server.utils import NetworkManager


class ProxyServer:
    """Integrated Proxy Server - Simplified logging version"""

    def __init__(self):
        self.dispatcher_thread = None
        self.server_socket = None
        self.health_thread = None
        self.host = config["proxy_host"]
        self.port = config["proxy_ip"]
        self.running = False
        self.shutdown_event = threading.Event()

        # Initialize network manager
        self.network = NetworkManager()

        # Task management
        self.task_queue: List[Dict[str, Any]] = []
        self.task_history: Dict[str, Dict] = {}

        # Server management
        self.servers: Dict[int, Dict[str, Any]] = {}
        self._rr_index = 0  # Round-robin index

        # Message handlers
        self.message_handlers = {
            'client_submit_task': self._handle_task_submission,
            'server_register': self._handle_server_register,
            'server_heartbeat': self._handle_heartbeat,
        }

        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    # Task management methods
    def submit_task(self, task_data: Dict) -> str:
        """Submit a task for processing"""
        task_id = task_data.get('task_id')
        if not task_id:
            return ""

        task_data.update({
            'submit_time': time.time(),
            'queue_time': time.time(),
            'status': 'queued'
        })

        self.task_queue.append(task_data)
        self.task_history[task_id] = task_data
        return task_id

    def validate_task_data(self, task_data: Dict) -> bool:
        """Validate task data completeness"""
        required_fields = ['task_id', 'task_name', 'function_code', 'function_name']
        return all(field in task_data for field in required_fields)

    def get_pending_task(self) -> Optional[Dict]:
        """Get next pending task from queue"""
        return self.task_queue.pop(0) if self.task_queue else None

    def requeue_task(self, task_data: Dict) -> None:
        """Requeue a task for retry"""
        retry_count = task_data.get('retry_count', 0) + 1
        task_data.update({
            'retry_count': retry_count,
            'last_retry': time.time(),
            'status': 'retrying'
        })
        self.task_queue.insert(0, task_data)

    def complete_task(self, task_id: str, result: Any = None) -> None:
        """Mark a task as completed"""
        if task_id in self.task_history:
            self.task_history[task_id].update({
                'status': 'completed',
                'complete_time': time.time(),
                'result': result
            })

    def get_task_by_id(self, task_id: str) -> Optional[Dict]:
        """Get task by ID from history"""
        return self.task_history.get(task_id)

    def get_task_stats(self) -> Dict:
        """Get task statistics"""
        return {
            'queued': len(self.task_queue),
            'total_history': len(self.task_history),
            'completed': len([t for t in self.task_history.values() if t.get('status') == 'completed'])
        }

    # Server management methods
    def register_server(self, server_port: int, host: str, addr: tuple) -> None:
        """Register a new server with the proxy"""
        if server_port not in self.servers:
            self.servers[server_port] = {
                'host': host,
                'port': server_port,
                'address': addr,
                'last_heartbeat': time.time(),
                'active': True,
                'health_score': 100
            }
            logger.info(f"Server registered: {host}:{server_port}")

    def update_heartbeat(self, server_port: int) -> None:
        """Update server heartbeat timestamp to indicate it's still alive"""
        if server_port in self.servers:
            self.servers[server_port]['last_heartbeat'] = time.time()

    def mark_server_inactive(self, server_port: int) -> None:
        """Mark server as inactive so it won't receive new tasks"""
        if server_port in self.servers:
            self.servers[server_port]['active'] = False
            logger.info(f"Server marked inactive: {server_port}")

    def select_best_server(self) -> Optional[Dict]:
        """Select best available server using round-robin algorithm"""
        active_servers = [
            (port, info) for port, info in self.servers.items()
            if info['active'] and time.time() - info['last_heartbeat'] < 60
        ]

        if not active_servers:
            logger.info("No active servers available")
            return None

        server_port, server_info = active_servers[self._rr_index % len(active_servers)]
        self._rr_index = (self._rr_index + 1) % len(active_servers)
        return server_info

    def health_check_all(self) -> int:
        """Perform health check on all registered servers"""
        active_count = 0

        for server_port, server_info in self.servers.items():
            try:
                # Send health check request to server
                response = self.network.health_check(server_info)

                if response and 'health_score' in response:
                    health_score = response['health_score']
                    server_info['health_score'] = health_score
                    server_info['active'] = health_score > 50

                    if health_score > 50:
                        active_count += 1
                        logger.info(f"Server {server_port} health check passed: score={health_score}")
                    else:
                        logger.info(f"Server {server_port} health check failed: score={health_score}")
                else:
                    server_info['health_score'] = 0
                    server_info['active'] = False
                    logger.info(f"Server {server_port} health check failed: no response")

            except Exception as e:
                server_info['health_score'] = 0
                server_info['active'] = False
                logger.info(f"Server {server_port} health check error: {e}")

        logger.info(f"Health check completed: {active_count}/{len(self.servers)} servers active")
        return active_count

    def get_server_stats(self) -> Dict:
        """Get server statistics"""
        active_servers = [s for s in self.servers.values() if s['active']]
        return {
            'total_servers': len(self.servers),
            'active_servers': len(active_servers),
            'servers': list(self.servers.keys())
        }

    # Signal handling
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals (Ctrl+C, termination signals)"""
        self.stop()

    # Server startup and operation
    def start(self):
        """Start the proxy server and all its components"""
        if self.running:
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

            # Start task dispatcher thread - handles distributing tasks to servers
            self.dispatcher_thread = threading.Thread(target=self._task_dispatcher_loop, daemon=True)
            self.dispatcher_thread.start()

            # Start health check thread - monitors server health periodically
            self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            self.health_thread.start()

            # Main connection loop - accepts incoming connections
            self._connection_loop()

        except Exception as e:
            logger.error(f"Server startup failed: {e}")
            self.stop()

    def _connection_loop(self):
        """Main connection handling loop - accepts client and server connections"""
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
            except OSError:
                if self.running and not self.shutdown_event.is_set():
                    break
            except Exception:
                continue

    def _handle_client(self, sock: socket.socket, addr: tuple):
        """Handle client connection - process incoming messages"""
        if self.shutdown_event.is_set():
            sock.close()
            return

        try:
            message = self.network.receive_message(sock)
            if message and 'type' in message and not self.shutdown_event.is_set():
                handler = self.message_handlers.get(message['type'])
                if handler:
                    handler(message, addr)
        except Exception:
            pass
        finally:
            sock.close()

    def _task_dispatcher_loop(self):
        """Task dispatcher main loop - distributes tasks to available servers"""
        while self.running and not self.shutdown_event.is_set():
            try:
                task = self.get_pending_task()
                if task:
                    if self.shutdown_event.is_set():
                        self.requeue_task(task)
                        continue

                    server = self.select_best_server()
                    if server:
                        success = self.network.send_to_server(server, {
                            'type': 'execute_task',
                            'task_data': task
                        })
                        if not success:
                            self.requeue_task(task)
                            self.mark_server_inactive(server['port'])
                            logger.info(f"Failed to send task to server {server['port']}, marked inactive")
                    else:
                        self.requeue_task(task)
                        if not self.shutdown_event.is_set():
                            time.sleep(2)
                else:
                    time.sleep(0.1)

            except Exception:
                time.sleep(0.1)

    def _health_check_loop(self):
        """Regular health check loop - monitors server health every 30 seconds"""
        while self.running and not self.shutdown_event.is_set():
            try:
                if not self.servers:
                    # Wait longer if no servers are registered
                    for _ in range(300):
                        if self.shutdown_event.is_set():
                            break
                        time.sleep(0.1)
                    continue

                # Perform health check on all servers
                active_count = self.health_check_all()

                # Adjust check interval based on active server count
                if active_count == 0:
                    check_interval = 10  # Check more frequently if no active servers
                else:
                    check_interval = 30  # Normal check interval

                # Interruptible wait for next health check
                for _ in range(check_interval * 10):
                    if self.shutdown_event.is_set():
                        break
                    time.sleep(0.1)

            except Exception:
                # Wait 5 seconds on error before retrying
                for _ in range(50):
                    if self.shutdown_event.is_set():
                        break
                    time.sleep(0.1)

    def _check_server_health(self, server_port: int, host: str) -> bool:
        """Check server health during registration - ensures only healthy servers are registered"""
        try:
            server_info = {'host': host, 'port': server_port}
            success = self.network.send_to_server(server_info, {
                'type': 'health_check',
                'timestamp': time.time()
            })

            if success:
                logger.info(f"Server {host}:{server_port} passed initial health check")
            else:
                logger.info(f"Server {host}:{server_port} failed initial health check")

            return success
        except Exception as e:
            logger.info(f"Server {host}:{server_port} health check error: {e}")
            return False

    # Message handler functions
    def _handle_task_submission(self, message: Dict, addr: tuple):
        """Handle task submission from clients - validates and queues tasks"""
        if self.shutdown_event.is_set():
            return

        task_data = message.get('task_data', {})
        if not self.validate_task_data(task_data):
            logger.info(f"Invalid task data received from {addr}")
            return

        task_id = self.submit_task(task_data)
        if task_id:
            logger.info(f"Task submitted: {task_data['task_name']} (ID: {task_id}) from {addr}")

    def _handle_server_register(self, message: Dict, addr: tuple):
        """Handle server registration - performs health check before registration"""
        if self.shutdown_event.is_set():
            return

        server_port = message.get('server_port')
        if server_port:
            host = message.get('host', addr[0])

            if server_port in self.servers:
                # Update heartbeat for existing server
                self.update_heartbeat(server_port)
                logger.info(f"Server {host}:{server_port} heartbeat updated")
            else:
                # Perform health check for new server registration
                logger.info(f"New server registration attempt: {host}:{server_port}")

                if self._check_server_health(server_port, host):
                    # Health check passed, register the server
                    self.register_server(server_port, host, addr)
                else:
                    # Health check failed
                    logger.info(f"Server {host}:{server_port} registration rejected - health check failed")

    def _handle_heartbeat(self, message: Dict, addr: tuple):
        """Handle heartbeat messages from servers - keeps server status up to date"""
        if self.shutdown_event.is_set():
            return

        server_port = message.get('server_port')
        if server_port in self.servers:
            self.update_heartbeat(server_port)
            logger.info(f"Server {server_port} heartbeat received")

    def stop(self):
        """Stop server gracefully - shuts down all components"""
        if not self.running:
            return

        logger.info("Starting server shutdown...")
        self.running = False
        self.shutdown_event.set()

        if hasattr(self, 'server_socket'):
            self.server_socket.close()

        logger.info("Server stopped")


# Global instance
proxy_server = ProxyServer()
