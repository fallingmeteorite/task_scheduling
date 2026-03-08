# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Remote Procedure Call (RPC) Server

Provides RPC interface for task scheduling operations.
Uses NetworkHandler for network communication.
"""

import socket
import threading
from typing import Any, List, Optional, Callable, Tuple

from task_scheduling.common import logger, config
from task_scheduling.rpc_server.utils import NetworkHandler
from task_scheduling.manager import task_scheduler, task_status_manager
from task_scheduling.scheduler import pause_api, resume_api, kill_api
from task_scheduling.server_webui import get_tasks_info


class RPCServer:
    """
    RPC Server for task scheduling operations.

    Exposes task scheduling functions via network interface for remote control.
    Automatically increments port if the specified port is in use.
    """

    def __init__(self) -> None:
        """
        Initialize RPC server.
        """
        self.base_host = config["control_host"]
        self.base_port = config["control_port"]
        self.host = self.base_host
        self.port = self.base_port
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.client_threads: List[threading.Thread] = []
        self._lock = threading.Lock()
        self.network_handler = NetworkHandler()
        self.max_port_attempts = config["max_port_attempts"]  # Maximum number of ports to try

        # Function mapping table to reduce if-else nesting
        self._function_map: dict[str, Callable] = {
            "add_ban_task_name": task_scheduler.add_ban_task_name,
            "remove_ban_task_name": task_scheduler.remove_ban_task_name,
            "cancel_the_queue_task_by_name": task_scheduler.cancel_the_queue_task_by_name,
            "get_tasks_info": get_tasks_info,
            "get_task_status": task_status_manager.get_task_status,
            "get_task_count": task_status_manager.get_task_count,
            "get_all_task_count": task_status_manager.get_all_task_count,
            "pause_api": pause_api,
            "resume_api": resume_api,
            "kill_api": kill_api,
        }

    def _find_available_port(self) -> Tuple[bool, int, Optional[str]]:
        """
        Find an available port starting from base_port.

        Returns:
            Tuple[bool, int, Optional[str]]: (success, port, error_message)
        """
        for attempt in range(self.max_port_attempts):
            current_port = self.base_port + attempt

            # Create a test socket to check if port is available
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1)

            try:
                test_socket.bind((self.base_host, current_port))
                test_socket.close()

                # Port is available
                if attempt > 0:
                    logger.info(f"Base port {self.base_port} in use, using port {current_port} instead")

                return True, current_port, None

            except OSError:
                test_socket.close()

                if attempt == self.max_port_attempts - 1:
                    error_msg = f"Failed to find available port after {self.max_port_attempts} attempts"
                    return False, self.base_port, error_msg

                # Continue to next port
                continue

            except Exception as error:
                test_socket.close()
                return False, self.base_port, f"Error checking port: {error}"

        return False, self.base_port, "Unknown error finding available port"

    def start(self) -> bool:
        """
        Start the RPC server with automatic port increment if needed.

        Returns:
            bool: True if server started successfully, False otherwise
        """
        # Find available port
        success, self.port, error_msg = self._find_available_port()
        if not success:
            logger.error(error_msg)
            return False

        # Create server socket with the available port
        self.server_socket = self.network_handler.create_server_socket(self.host, self.port)
        if not self.server_socket:
            logger.error(f"Failed to create server socket on {self.host}:{self.port}")
            return False

        self.running = True
        logger.info(f"Task RPC Server started on {self.host}:{self.port}")

        # Update config with actual port being used
        config["control_port"] = self.port

        try:
            self._accept_connections()
            return True
        except Exception as error:
            logger.error(f"Server error: {error}")
            return False
        finally:
            self.stop()

    def _accept_connections(self) -> None:
        """Accept and handle incoming client connections."""
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                self._handle_new_client(client_socket, client_address)
            except socket.timeout:
                continue  # Timeout is expected for checking running status
            except (KeyboardInterrupt, OSError):
                break  # Server socket closed or interrupt
            except Exception as error:
                if self.running:
                    logger.error(f"Error accepting connection: {error}")

    def _handle_new_client(self, client_socket: socket.socket, client_address: tuple) -> None:
        """Handle new client connection."""
        logger.info(f"New connection from {client_address}")

        # Create new thread for each client
        client_thread = threading.Thread(
            target=self._client_handler,
            args=(client_socket, client_address),
            name=f"Client-{client_address}",
            daemon=True
        )
        client_thread.start()

        # Track threads for cleanup
        with self._lock:
            self.client_threads.append(client_thread)

    def _client_handler(self, client_socket: socket.socket, client_address: tuple) -> None:
        """Main client handler loop."""
        client_name = threading.current_thread().name

        try:
            while self.running:
                request = self.network_handler.receive_message(client_socket)
                if request is None:
                    break

                logger.debug(f"Received request from {client_address}: {request.get('function')}")
                response = self._process_request(request)
                self.network_handler.send_message(client_socket, response)

        except (ConnectionError, BrokenPipeError):
            logger.error(f"Client {client_address} disconnected unexpectedly")
        except Exception as error:
            if self.running:
                logger.error(f"Error handling client {client_address}: {error}")
        finally:
            self._cleanup_client(client_socket, client_name)

    def _cleanup_client(self, client_socket: socket.socket, client_name: str) -> None:
        """Clean up client resources."""
        client_socket.close()
        logger.info(f"Client handler {client_name} terminated")

    def _process_request(self, request: dict) -> dict:
        """
        Process RPC request.

        Args:
            request: Request dictionary containing function name and arguments

        Returns:
            dict: Response dictionary with result or error
        """
        function_name = request.get('function')
        args = request.get('args', [])
        kwargs = request.get('kwargs', {})

        try:
            result = self._execute_function(function_name, *args, **kwargs)
            return {
                'success': True,
                'result': result,
                'function': function_name
            }
        except Exception as error:
            return {
                'success': False,
                'error': str(error),
                'function': function_name or 'unknown'
            }

    def _execute_function(self, function_name: str, *args, **kwargs) -> Any:
        """
        Execute specific function call.

        Args:
            function_name: Name of function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Any: Function execution result

        Raises:
            ValueError: If function name is unknown
        """
        func = self._function_map.get(function_name)
        if not func:
            raise ValueError(f"Unknown function: {function_name}")

        return func(*args, **kwargs)

    def stop(self) -> None:
        """Stop server with graceful shutdown."""
        if not self.running:
            return

        logger.warning("Initiating graceful shutdown...")
        self.running = False

        # Close server socket
        if self.server_socket:
            self.server_socket.close()

        logger.info("Server shutdown complete")

    def get_actual_address(self) -> Tuple[str, int]:
        """
        Get the actual host and port the server is running on.

        Returns:
            Tuple[str, int]: (host, port)
        """
        return self.host, self.port
