# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Client Network Communication Module

Handles network communication with the proxy server using fire-and-forget approach.
"""

import socket
import pickle

from typing import Dict, Any
from task_scheduling.common import logger


def send_request(request_data: Dict[str, Any]) -> None:
    """
    Send request to proxy server using fire-and-forget approach.

    This function establishes a TCP connection to the proxy server, sends serialized
    request data, and immediately closes the connection without waiting for response.
    Delivery is not guaranteed with this approach.

    Args:
        request_data: Dictionary containing task information to be sent to proxy server

    Note:
        Uses fire-and-forget pattern - function returns immediately after sending
        without waiting for server response or confirmation
    """
    client_socket = None
    try:
        # Create TCP socket connection to proxy server
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(10)  # Set connection timeout only

        # Establish connection to proxy server
        client_socket.connect(('localhost', 8999))

        # Serialize request data and send
        request_bytes = pickle.dumps(request_data)
        client_socket.sendall(request_bytes)

    except KeyboardInterrupt:
        # Silently handle keyboard interrupts
        pass

    except Exception as error:
        logger.error(f"Failed to send request to proxy server: {error}")

    finally:
        # Ensure socket is properly closed even if errors occur during execution
        if client_socket:
            client_socket.close()
