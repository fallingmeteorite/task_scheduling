# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Network Manager Module

This module provides network communication management for client-server interactions,
including message sending, receiving, and health checks.

Key Features:
    - Secure socket communication with timeout handling
    - Message serialization using pickle
    - Health check mechanism for server availability
    - Error handling and connection management

Classes:
    NetworkManager: Main class for managing network operations

Global Variables:
    None
"""

import time
import socket
import pickle

from typing import Dict, Optional
from task_scheduling.common import logger


class NetworkManager:
    """
    Network Communication Management - All network operations are centralized here.

    This class provides a comprehensive network communication solution including
    message sending, receiving, and server health monitoring.

    Methods:
        send_to_server: Send messages to server with connection handling
        receive_message: Receive complete messages from socket with timeout
        health_check: Perform health check on server with full validation
    """

    @staticmethod
    def send_to_server(server_info: Dict, message: Dict) -> bool:
        """
        Send message to server.

        Establishes a TCP connection to the server and sends a serialized message.
        Handles connection errors and timeouts gracefully.

        Args:
            server_info: Dictionary containing server connection information:
                - host: Server hostname or IP address
                - port: Server port number
            message: Dictionary containing the message to send

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10.0)
                sock.connect((server_info['host'], server_info['port']))
                sock.send(pickle.dumps(message))
            return True
        except Exception as error:
            logger.error(f"Failed to send message to server {server_info}: {error}")
            return False

    @staticmethod
    def receive_message(sock: socket.socket, timeout: float = 5.0) -> Optional[Dict]:
        """
        Receive complete message from socket.

        Receives data from socket in chunks and attempts to deserialize it.
        Handles partial messages and deserialization errors.

        Args:
            sock: Connected socket object for receiving data
            timeout: Timeout value for socket operations in seconds

        Returns:
            Optional[Dict]: Deserialized message dictionary if successful, None otherwise
        """
        try:
            data = b""
            sock.settimeout(timeout)

            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                try:
                    return pickle.loads(data)
                except (pickle.UnpicklingError, EOFError):
                    continue
        except Exception as error:
            logger.error(f"Failed to receive message from socket: {error}")
            return None

    @staticmethod
    def health_check(server_info: Dict) -> Optional[Dict]:
        """
        Health check - Complete validation process.

        Performs a health check on the server by sending a health check message
        and validating the response.

        Args:
            server_info: Dictionary containing server connection information:
                - host: Server hostname or IP address
                - port: Server port number

        Returns:
            Optional[Dict]: Health response dictionary if server is healthy, None otherwise
        """
        try:
            host, port = server_info['host'], server_info['port']
            health_msg = {'type': 'health_check', 'timestamp': time.time()}

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5.0)
                sock.connect((host, port))
                sock.send(pickle.dumps(health_msg))

                response = NetworkManager.receive_message(sock)
                return response if response and response.get('type') == 'health_response' else None

        except Exception as error:
            logger.error(f"Health check failed for server {server_info}: {error}")
            return None
