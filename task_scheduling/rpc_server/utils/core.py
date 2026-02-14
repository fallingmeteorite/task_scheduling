# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Network Communication Handler

Provides reusable network communication utilities with length-prefix protocol.
"""

import socket
import struct
import threading
from typing import Any, Optional

import dill

from task_scheduling.common import logger


class NetworkHandler:
    """
    Network communication handler with length-prefix protocol.

    Provides methods for sending and receiving serialized data over sockets.
    """

    def __init__(self, timeout: float = 5.0, chunk_size: int = 4096):
        """
        Initialize network handler.

        Args:
            timeout: Socket timeout in seconds (default: 5.0)
            chunk_size: Chunk size for data transmission (default: 4096)
        """
        self.timeout = timeout
        self.chunk_size = chunk_size
        self._lock = threading.Lock()

    def send_message(self, sock: socket.socket, data: Any) -> bool:
        """
        Send serialized data with length prefix.

        Args:
            sock: Socket connection
            data: Data to send (will be serialized)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._lock:
                # Serialize data
                serialized_data = dill.dumps(data)

                # Create length prefix (big-endian 4-byte integer)
                data_length = len(serialized_data)
                length_prefix = struct.pack('>I', data_length)

                # Send length prefix
                sock.sendall(length_prefix)

                # Send actual data
                sock.sendall(serialized_data)

            return True

        except Exception as error:
            logger.error(f"Error sending message: {error}")
            return False

    def receive_message(self, sock: socket.socket) -> Optional[Any]:
        """
        Receive serialized data with length prefix.

        Args:
            sock: Socket connection

        Returns:
            Optional[Any]: Deserialized data or None if failed
        """
        try:
            # Set timeout
            sock.settimeout(self.timeout)

            # Receive length prefix (4 bytes)
            length_data = self._recv_exact(sock, 4)
            if not length_data:
                return None

            # Unpack length
            data_length = struct.unpack('>I', length_data)[0]

            # Receive actual data
            serialized_data = self._recv_exact(sock, data_length)
            if not serialized_data:
                return None

            # Deserialize data
            return dill.loads(serialized_data)

        except socket.timeout:
            logger.error("Receive timeout")
            return None
        except Exception as error:
            logger.error(f"Error receiving message: {error}")
            return None
        finally:
            # Reset to blocking mode
            sock.setblocking(True)

    def _recv_exact(self, sock: socket.socket, n: int) -> Optional[bytes]:
        """
        Receive exact number of bytes.

        Args:
            sock: Socket connection
            n: Number of bytes to receive

        Returns:
            Optional[bytes]: Received bytes or None if incomplete
        """
        data = b''
        while len(data) < n:
            try:
                chunk = sock.recv(min(self.chunk_size, n - len(data)))
                if not chunk:  # Connection closed
                    return None
                data += chunk
            except socket.timeout:
                continue
        return data

    def create_server_socket(self, host: str, port: int, backlog: int = 5) -> Optional[socket.socket]:
        """
        Create and configure a server socket.

        Args:
            host: Server host address
            port: Server port
            backlog: Maximum queued connections (default: 5)

        Returns:
            Optional[socket.socket]: Configured server socket or None if failed
        """
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(backlog)
            server_socket.settimeout(1.0)  # For checking running status

            return server_socket

        except Exception as error:
            logger.error(f"Error creating server socket: {error}")
            return None

    def create_client_socket(self, host: str, port: int) -> Optional[socket.socket]:
        """
        Create and connect a client socket.

        Args:
            host: Server host address
            port: Server port

        Returns:
            Optional[socket.socket]: Connected socket or None if failed
        """
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(self.timeout)
            client_socket.connect((host, port))
            return client_socket

        except Exception as error:
            logger.error(f"Error creating client socket: {error}")
            return None
