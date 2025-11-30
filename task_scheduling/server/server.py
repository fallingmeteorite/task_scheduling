# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Task Server Main Module

Task server main entry point, integrating server startup, connection acceptance, and main loop.
"""

import socket
import signal
import threading
import pickle
import time

from typing import Any, Optional, Dict
from task_scheduling.common import logger, config
from task_scheduling.server.utils import TaskServerCore


class TaskServer:
    """
    Task server, receives and executes tasks from broker.
    """

    def __init__(self) -> None:
        """
        Initialize task server.
        """
        self.host = "localhost"
        self.port = config["server_ip"]
        self.broker_host = "localhost"
        self.broker_port = config["proxy_ip"]
        self.max_port_attempts = config["max_port_attempts"]
        self.running = True
        self.server_socket: Optional[socket.socket] = None
        self.broker_socket: Optional[socket.socket] = None
        self.shutdown_event = threading.Event()

        # Initialize core components
        self.core = TaskServerCore()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """
        Handle interrupt signals for graceful shutdown.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.warning("Received interrupt signal, shutting down...")
        self.stop()

    @staticmethod
    def receive_message(client_socket: socket.socket, timeout: float = 5.0) -> Optional[Dict]:
        """Receive message - fixed version"""
        try:
            client_socket.settimeout(timeout)

            # Method 1: Directly try to receive pickle data
            data = b""
            start_time = time.time()

            while time.time() - start_time < timeout:
                try:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    data += chunk

                    # Try to parse pickle data
                    try:
                        message = pickle.loads(data)
                        return message
                    except (pickle.UnpicklingError, EOFError):
                        # Data incomplete, continue receiving
                        continue

                except socket.timeout:
                    # No data within timeout period, continue waiting
                    continue

            # If no complete data after timeout, try to parse existing data
            if data:
                return pickle.loads(data)

            return None

        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None

    @staticmethod
    def send_message(client_socket: socket.socket, message: Dict) -> bool:
        """Send message"""
        try:
            data = pickle.dumps(message)
            client_socket.sendall(data)  # Use sendall to ensure all data is sent
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def create_health_message(self, health_score: int) -> Dict:
        """Create health check response message"""
        return {
            'type': 'health_response',
            'health_score': health_score,
            'timestamp': time.time(),
            'server_port': self.port,
            'status': 'healthy'
        }

    def _find_available_port(self) -> int:
        """
        Find available port starting from configured port.
        """
        current_port = self.port
        attempts = 0

        while attempts < self.max_port_attempts:
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_socket.bind((self.host, current_port))
                test_socket.close()

                if current_port != self.port:
                    logger.info(f"Port {self.port} is occupied, using port {current_port} instead")
                return current_port

            except OSError as e:
                if e.errno in [48, 98]:
                    logger.debug(f"Port {current_port} is occupied, trying next port...")
                    current_port += 1
                    attempts += 1
                else:
                    raise e

        raise Exception(f"No available port found after {self.max_port_attempts} attempts")

    def _handle_health_check(self, client_socket: socket.socket) -> None:
        """
        Handle health check requests from broker server - fixed version.
        """
        try:
            logger.debug("Health check request received, starting detection...")

            # Immediately send health check response without waiting to receive message
            # because the broker server may have sent a message, but we don't need to read it
            health_score = self.core.get_health_status()

            # Create and send health response
            health_response = self.create_health_message(health_score)

            if self.send_message(client_socket, health_response):
                logger.debug(f"Health response sent successfully, score: {health_score}%")
            else:
                logger.error("Health response sending failed")

        except Exception as error:
            logger.error(f"Error handling health check: {error}")
        finally:
            client_socket.close()

    def _handle_client_connection(self, client_socket: socket.socket, addr: tuple) -> None:
        """
        Handle incoming client connections and determine message type - simplified version.
        """
        if self.shutdown_event.is_set():
            client_socket.close()
            return

        try:
            logger.debug(f"Starting to handle connection from {addr}")

            # Receive message (with shorter timeout)
            message = self.receive_message(client_socket, timeout=2.0)

            if message:
                message_type = message.get('type', '')
                logger.debug(f"Received message type from {addr}: '{message_type}'")

                if message_type == 'health_check':
                    logger.debug(f"Health check request from {addr}")
                    self._handle_health_check(client_socket)
                elif message_type == 'execute_task':
                    logger.debug(f"Task execution request from {addr}")
                    self._handle_task_message(client_socket, addr, message)
                else:
                    logger.debug(f"Unknown message type: {message_type}")
                    client_socket.close()
            else:
                # No message received, treat as health check connection
                logger.debug(f"No clear message received, treating as health check from {addr}")
                self._handle_health_check(client_socket)

        except Exception as error:
            logger.error(f"Error handling client connection {addr}: {error}")
            client_socket.close()

    def _handle_task_message(self, client_socket: socket.socket, addr: tuple, message: Dict[str, Any]) -> None:
        """
        Handle task messages.
        """
        try:
            task_data = message.get('task_data', {})
            task_name = task_data.get('task_name', 'Unknown task')
            # Execute task
            self.core.execute_received_task(task_data)

        except Exception as error:
            logger.error(f"Error handling task message: {error}")
        finally:
            client_socket.close()
            logger.debug(f"Task processing completed, closing connection with {addr}")

    def start(self) -> None:
        """
        Start task server and begin listening for tasks.
        """
        try:
            # Find available port
            available_port = self._find_available_port()
            self.port = available_port

            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.server_socket.settimeout(1.0)

            logger.info(f"Task server started on {self.host}:{self.port}")

            # Register with broker
            try:
                self.broker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.broker_socket.settimeout(5.0)
                self.broker_socket.connect((self.broker_host, self.broker_port))

                register_message = {
                    'type': 'server_register',
                    'server_port': self.port,
                    'host': self.host
                }
                self.broker_socket.send(pickle.dumps(register_message))
                logger.debug(f"Registered with broker server: {self.broker_host}:{self.broker_port}")

            except Exception as e:
                logger.error(f"Failed to connect to broker: {e}")

            # Start accepting connections
            self._accept_connections()

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
        finally:
            self.stop()

    def _accept_connections(self) -> None:
        """
        Accept incoming connections from broker and clients.
        """
        logger.debug("Starting to accept connections...")
        while self.running and not self.shutdown_event.is_set():
            try:
                client_socket, addr = self.server_socket.accept()
                logger.debug(f"Connection received from {addr}")

                client_thread = threading.Thread(
                    target=self._handle_client_connection,
                    args=(client_socket, addr), daemon=True
                )
                client_thread.start()

            except socket.timeout:
                continue
            except OSError as e:
                if self.running and not self.shutdown_event.is_set():
                    logger.error(f"Error accepting connection: {e}")
                break
            except Exception as e:
                if self.running and not self.shutdown_event.is_set():
                    logger.error(f"Unknown error accepting connection: {e}")

    def stop(self) -> None:
        """
        Stop server and cleanup resources.
        """
        if not self.running:
            return

        self.running = False
        self.shutdown_event.set()
        logger.warning("Stopping task server...")

        if self.server_socket:
            self.server_socket.close()

        if self.broker_socket:
            self.broker_socket.close()

        self.core.shutdown()

        logger.warning("Task server stopped")


# Create global server instance
task_server = TaskServer()
