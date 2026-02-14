# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Task Server Main Module

Task server main entry point, integrating server startup, connection acceptance, and main loop.
"""

import socket
import threading
import time
from typing import Any, Optional, Dict

import dill

from task_scheduling.common import logger, config
from task_scheduling.main_server.utils import TaskServerCore


class TaskServer:
    """
    Task server, receives and executes tasks from broker.
    """

    def __init__(self) -> None:
        """
        Initialize task server.
        """
        self.host = config["server_host"]
        self.port = config["server_port"]
        self.broker_host = config["proxy_host"]
        self.broker_port = config["proxy_port"]
        self.max_port_attempts = config["max_port_attempts"]
        self.running = True
        self.server_socket: Optional[socket.socket] = None
        self.broker_socket: Optional[socket.socket] = None
        self.shutdown_event = threading.Event()
        self.broker_connected = False  # Add broker connection status flag

        # Initialize core components
        self.core = TaskServerCore()

        # Add message handler dictionary
        self.message_handlers = {
            'proxy_shutdown': self._handle_proxy_shutdown,
        }

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
                        message = dill.loads(data)
                        return message
                    except (dill.UnpicklingError, EOFError):
                        # Data incomplete, continue receiving
                        continue

                except socket.timeout:
                    # No data within timeout period, continue waiting
                    continue

            # If no complete data after timeout, try to parse existing data
            if data:
                return dill.loads(data)

            return None

        except Exception as error:
            logger.error(f"Error receiving message: {error}")
            return None

    @staticmethod
    def send_message(client_socket: socket.socket, message: Dict) -> bool:
        """Send message"""
        try:
            data = dill.dumps(message)
            client_socket.sendall(data)  # Use sendall to ensure all data is sent
            return True
        except Exception as error:
            logger.error(f"Error sending message: {error}")
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

            except OSError as error:
                if error.errno in [48, 98]:
                    current_port += 1
                    attempts += 1
                else:
                    raise error

        raise Exception(f"No available port found after {self.max_port_attempts} attempts")

    def _is_broker_connection_alive(self) -> bool:
        """
        Check if broker connection is still alive.
        """
        if not self.broker_socket:
            return False

        try:
            # Use non-blocking method to check socket status
            self.broker_socket.setblocking(False)

            # Try to send empty data to check connection
            try:
                self.broker_socket.send(b'')
            except socket.error as e:
                # If error is EAGAIN or EWOULDBLOCK, socket is still writable
                if e.errno in [11, 35]:  # EAGAIN or EWOULDBLOCK
                    pass
                else:
                    return False
            finally:
                self.broker_socket.setblocking(True)

            # Also try to get socket error status
            try:
                # Check if socket has pending errors
                self.broker_socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            except:
                return False

            return True

        except Exception as error:
            logger.debug(f"Connection check failed: {error}")
            return False

    def _close_broker_socket(self) -> None:
        """
        Safely close broker socket.
        """
        if self.broker_socket:
            try:
                self.broker_socket.close()
            except:
                pass
            finally:
                self.broker_socket = None

    def _register_with_broker(self) -> bool:
        """
        Register with broker server with retry mechanism.
        Returns True if registration successful, False otherwise.
        """
        try:
            # Close any existing connection first
            self._close_broker_socket()

            # Create new socket connection
            broker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            broker_socket.settimeout(2.0)  # Set short timeout

            try:
                broker_socket.connect((self.broker_host, self.broker_port))

                register_message = {
                    'type': 'server_register',
                    'server_port': self.port,
                    'host': self.host
                }

                # Send registration message
                broker_socket.send(dill.dumps(register_message))

                self.broker_socket = broker_socket
                self.broker_connected = True
                logger.info(f"Successfully registered with broker server at {self.broker_host}:{self.broker_port}")
                return True

            except Exception as e:
                broker_socket.close()
                raise e

        except Exception as error:
            self.broker_connected = False
            logger.warning(f"Failed to connect to broker: {error}")
            return False

    def _handle_proxy_shutdown(self, message: Dict):
        """Handle proxy server shutdown notification"""
        logger.warning("Received proxy shutdown notification")
        logger.warning("Proxy server is shutting down, will attempt to reconnect...")

        # Mark broker connection as disconnected
        self.broker_connected = False

        # Close current broker socket
        self._close_broker_socket()

        logger.warning(f"Proxy shutdown!")

    def _broker_registration_loop(self) -> None:
        """
        Continuous broker registration loop with 0.1 second interval.
        Handles reconnection when broker restarts.
        """
        logger.info("Starting broker registration loop...")
        connection_check_interval = 1.0  # Check interval after successful connection
        last_check_time = 0

        while self.running and not self.shutdown_event.is_set():
            try:
                current_time = time.time()

                # If marked as connected, periodically check if connection is actually valid
                if self.broker_connected:
                    # Check connection status at intervals
                    if current_time - last_check_time >= connection_check_interval:
                        if not self._is_broker_connection_alive():
                            logger.warning("Broker connection lost, attempting to reconnect...")
                            self.broker_connected = False
                            self._close_broker_socket()
                        last_check_time = current_time
                    else:
                        time.sleep(0.1)  # Brief sleep to avoid CPU idle spinning
                        continue

                # If not connected, try to register
                if not self.broker_connected:
                    if self._register_with_broker():
                        logger.info("Broker connection established")
                        last_check_time = time.time()  # Reset check time
                    else:
                        # Registration failed, wait 0.1 seconds and retry
                        time.sleep(0.1)
                else:
                    # Connection normal, brief sleep
                    time.sleep(0.1)

            except Exception as error:
                logger.error(f"Error in broker registration loop: {error}")
                self.broker_connected = False
                self._close_broker_socket()
                time.sleep(0.1)  # Wait 0.1 seconds after error before retry

    def _handle_health_check(self, client_socket: socket.socket) -> None:
        """
        Handle health check requests from broker server - fixed version.
        """
        try:
            health_score = self.core.get_health_status()
            health_response = self.create_health_message(health_score)

            if self.send_message(client_socket, health_response):
                logger.debug(f"Health response sent, score: {health_score}%")

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
            # Receive message (with shorter timeout)
            message = self.receive_message(client_socket, timeout=2.0)

            if message:
                message_type = message.get('type', '')

                if message_type == 'health_check':
                    self._handle_health_check(client_socket)
                elif message_type == 'execute_task':
                    self._handle_task_message(client_socket, addr, message)
                elif message_type in self.message_handlers:
                    # Handle other types of messages (such as proxy shutdown notification)
                    handler = self.message_handlers[message_type]
                    handler(message)
                    client_socket.close()
                else:
                    logger.warning(f"Unknown message type from {addr}: {message_type}")
                    client_socket.close()
            else:
                # No message received, treat as health check connection
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
            logger.info(f"Executing task: {task_name} from {addr}")

            # Execute task
            self.core.execute_received_task(task_data)

        except Exception as error:
            logger.error(f"Error handling task message: {error}")
        finally:
            client_socket.close()

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

            # Start broker registration thread
            registration_thread = threading.Thread(target=self._broker_registration_loop, daemon=True)
            registration_thread.start()

            # Start accepting connections
            self._accept_connections()

        except Exception as error:
            logger.error(f"Failed to start server: {error}")
        finally:
            self.stop()

    def _accept_connections(self) -> None:
        """
        Accept incoming connections from broker and clients.
        """
        logger.info("Server ready to accept connections")
        while self.running and not self.shutdown_event.is_set():
            try:
                client_socket, addr = self.server_socket.accept()

                client_thread = threading.Thread(
                    target=self._handle_client_connection,
                    args=(client_socket, addr), daemon=True
                )
                client_thread.start()

            except socket.timeout:
                continue
            except OSError as error:
                if self.running and not self.shutdown_event.is_set():
                    logger.error(f"Error accepting connection: {error}")
                break
            except Exception as error:
                if self.running and not self.shutdown_event.is_set():
                    logger.error(f"Unknown error accepting connection: {error}")

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

        self._close_broker_socket()  # Use encapsulated method to close broker socket

        self.core.shutdown()

        logger.warning("Task server stopped")
