# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Network Utilities Module

Provides network communication and socket operations, integrating connection handling and protocol processing.
"""

import socket
import pickle
import time

from typing import Dict, Any, Optional
from task_scheduling.common import logger


def create_server_socket(host: str, port: int) -> Optional[socket.socket]:
    """
    Create and configure server socket.

    Args:
        host: Server host address
        port: Server port number

    Returns:
        Optional[socket.socket]: Configured server socket, None if failed
    """
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        server_socket.settimeout(1.0)
        return server_socket
    except Exception as e:
        logger.error(f"Failed to create server socket: {e}")
        return None


def register_with_broker(broker_host: str, broker_port: int, server_host: str, server_port: int) -> Optional[
    socket.socket]:
    """
    Register server with task broker.

    Args:
        broker_host: Broker host address
        broker_port: Broker port number
        server_host: Server host address
        server_port: Server port number

    Returns:
        Optional[socket.socket]: Broker socket connection, None if failed
    """
    try:
        broker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        broker_socket.connect((broker_host, broker_port))

        register_msg = {
            'type': 'server_register',
            'server_port': server_port,
            'host': server_host
        }

        data = pickle.dumps(register_msg)
        broker_socket.send(data)

        logger.info(f"Server registered with broker: {server_host}:{server_port}")
        return broker_socket

    except Exception as e:
        logger.error(f"Failed to register with broker: {e}")
        return None


def send_message(socket_obj: socket.socket, message: Dict[str, Any]) -> bool:
    """
    Send message using length-prefix protocol.

    Args:
        socket_obj: Socket object
        message: Message dictionary to send

    Returns:
        bool: True if send successful, False otherwise
    """
    try:
        data = pickle.dumps(message)
        data_length = len(data)

        # Send length first (4 bytes), then data
        socket_obj.sendall(data_length.to_bytes(4, byteorder='big'))
        socket_obj.sendall(data)
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False


def receive_message(socket_obj: socket.socket, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """
    Receive complete message (compatible with both length-prefix and direct pickle protocols).

    Args:
        socket_obj: Socket object
        timeout: Receive timeout in seconds

    Returns:
        Optional[Dict]: Received message, None on error
    """
    try:
        socket_obj.settimeout(timeout)

        # First try to receive 4 bytes as length prefix
        length_data = socket_obj.recv(4, socket.MSG_PEEK)  # Peek data without removing from buffer
        if not length_data:
            return None

        # Check if it's a reasonable length value (less than 10MB)
        potential_length = int.from_bytes(length_data, byteorder='big')
        if potential_length < 0 or potential_length > 10 * 1024 * 1024:  # 10MB limit
            # Likely direct pickle data without length prefix
            return _receive_direct_pickle(socket_obj)
        else:
            # Use length-prefix protocol
            return _receive_length_prefixed(socket_obj)

    except socket.timeout:
        return None
    except Exception as e:
        logger.error(f"Error receiving message: {e}")
        return None


def _receive_length_prefixed(socket_obj: socket.socket) -> Optional[Dict[str, Any]]:
    """
    Receive message using length-prefix protocol.

    Args:
        socket_obj: Socket object

    Returns:
        Optional[Dict]: Received message
    """
    try:
        # Receive message length (first 4 bytes)
        length_data = socket_obj.recv(4)
        if not length_data:
            return None

        message_length = int.from_bytes(length_data, byteorder='big')

        # Receive actual message data
        message_data = b''
        while len(message_data) < message_length:
            chunk = socket_obj.recv(min(4096, message_length - len(message_data)))
            if not chunk:
                break
            message_data += chunk

        if len(message_data) != message_length:
            logger.warning(f"Incomplete message: expected {message_length}, got {len(message_data)}")
            return None

        # Parse message
        message = pickle.loads(message_data)
        return message

    except Exception as e:
        logger.error(f"Error receiving length-prefixed message: {e}")
        return None


def _receive_direct_pickle(socket_obj: socket.socket) -> Optional[Dict[str, Any]]:
    """
    Receive direct pickle data (without length prefix).

    Args:
        socket_obj: Socket object

    Returns:
        Optional[Dict]: Received message
    """
    try:
        message_data = b""
        socket_obj.settimeout(2.0)  # Set shorter timeout

        while True:
            try:
                chunk = socket_obj.recv(4096)
                if not chunk:
                    break
                message_data += chunk
                # Try to parse pickle to check if message is complete
                try:
                    message = pickle.loads(message_data)
                    return message
                except (pickle.UnpicklingError, EOFError):
                    # Message not complete yet, continue receiving
                    continue
            except socket.timeout:
                # Timeout, consider message reception complete
                break

        # Final parsing attempt
        if message_data:
            try:
                message = pickle.loads(message_data)
                return message
            except (pickle.UnpicklingError, EOFError) as e:
                logger.error(f"Failed to parse direct pickle data: {e}")
                return None

        return None

    except Exception as e:
        logger.error(f"Error receiving direct pickle message: {e}")
        return None


def create_health_message(health_score: int) -> Dict[str, Any]:
    """
    Create health check response message.

    Args:
        health_score: Health score

    Returns:
        Dict: Health check message
    """
    return {
        'type': 'health_response',
        'health_score': health_score,
        'timestamp': time.time()
    }


def create_task_message(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create task message.

    Args:
        task_data: Task data

    Returns:
        Dict: Task message
    """
    return {
        'type': 'execute_task',
        'task_data': task_data
    }
