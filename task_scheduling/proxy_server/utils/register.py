# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""
Server Manager Module

This module provides server management functionality for handling server registration,
health monitoring, and server selection.

Key Features:
    - Server registration and heartbeat tracking
    - Health monitoring and status management
    - Round-robin server selection algorithm
    - Server statistics and status reporting

Classes:
    ServerManager: Main class for managing server operations and status

Global Variables:
    None
"""

import time

from typing import Dict, Any, Optional
from task_scheduling.common import logger


class ServerManager:
    """
    Server Management - All server-related operations are centralized here.

    This class provides comprehensive server management including registration,
    health monitoring, status tracking, and server selection.

    Attributes:
        servers: Dictionary of registered servers with their status information
        _rr_index: Round-robin index for server selection

    Methods:
        register_server: Register a new server with initial status
        update_heartbeat: Update server heartbeat timestamp
        mark_server_inactive: Mark server as inactive
        select_best_server: Select best available server using round-robin
        health_check_all: Perform health check on all registered servers
        get_server_stats: Generate statistics about server status
    """

    def __init__(self) -> None:
        """
        Initialize ServerManager with empty server registry.

        Initializes:
            servers: Empty dictionary for server registry
            _rr_index: Round-robin index starting at 0
        """
        self.servers: Dict[int, Dict[str, Any]] = {}
        self._rr_index = 0  # Round-robin index

    def register_server(self, server_port: int, host: str, addr: tuple) -> None:
        """
        Register server.

        Adds a new server to the registry with initial status values
        including heartbeat timestamp and health score.

        Args:
            server_port: Server port number used as unique identifier
            host: Server hostname or IP address
            addr: Server address tuple

        Returns:
            None
        """
        try:
            self.servers[server_port] = {
                'host': host,
                'port': server_port,
                'address': addr,
                'last_heartbeat': time.time(),
                'active': True,
                'health_score': 100
            }
        except Exception as e:
            logger.error(f"Failed to register server {server_port} at {host}: {str(e)}")

    def update_heartbeat(self, server_port: int) -> None:
        """
        Update heartbeat.

        Updates the last heartbeat timestamp for a server to indicate
        it's still active and responsive.

        Args:
            server_port: Server port number to update

        Returns:
            None
        """
        try:
            if server_port in self.servers:
                self.servers[server_port]['last_heartbeat'] = time.time()
        except Exception as e:
            logger.error(f"Failed to update heartbeat for server {server_port}: {str(e)}")

    def mark_server_inactive(self, server_port: int) -> None:
        """
        Mark server as inactive.

        Sets a server's active status to False, indicating it should
        not be used for task processing.

        Args:
            server_port: Server port number to mark inactive

        Returns:
            None
        """
        try:
            if server_port in self.servers:
                self.servers[server_port]['active'] = False
        except Exception as e:
            logger.error(f"Failed to mark server {server_port} as inactive: {str(e)}")

    def select_best_server(self) -> Optional[Dict]:
        """
        Select best server.

        Uses round-robin algorithm to select from active servers that
        have had recent heartbeats (within 60 seconds).

        Returns:
            Optional[Dict]: Selected server information if available, None otherwise
        """
        try:
            active_servers = [
                (port, info) for port, info in self.servers.items()
                if info['active'] and time.time() - info['last_heartbeat'] < 60
            ]

            if not active_servers:
                return None

            # Round-robin selection
            server_port, server_info = active_servers[self._rr_index % len(active_servers)]
            self._rr_index = (self._rr_index + 1) % len(active_servers)

            return server_info
        except Exception as e:
            logger.error(f"Failed to select best server: {str(e)}")
            return None

    def health_check_all(self, network: Any) -> int:
        """
        Check all server health status.

        Performs health checks on all registered servers and updates
        their status based on the health check results.

        Args:
            network: Network manager instance for performing health checks

        Returns:
            int: Number of active servers after health checks
        """
        active_count = 0

        if not self.servers:
            return 0

        for server_port, server_info in self.servers.items():
            try:
                response = network.health_check(server_info)

                if response and 'health_score' in response:
                    health_score = response['health_score']
                    server_info['health_score'] = health_score
                    server_info['active'] = health_score > 50

                    if health_score > 50:
                        active_count += 1
                else:
                    # No response or invalid format from health check
                    server_info['health_score'] = 0
                    server_info['active'] = False

            except Exception as error:
                logger.error(f"Health check failed for server {server_port}: {str(error)}")
                # Error during health check, mark server as inactive
                server_info['health_score'] = 0
                server_info['active'] = False

        return active_count

    def get_server_stats(self) -> Dict:
        """
        Get server statistics.

        Generates comprehensive statistics about the current state
        of registered servers.

        Returns:
            Dict: Statistics including:
                - total_servers: Total number of registered servers
                - active_servers: Number of currently active servers
                - servers: List of all server port numbers
        """
        try:
            active_servers = [s for s in self.servers.values() if s['active']]
            return {
                'total_servers': len(self.servers),
                'active_servers': len(active_servers),
                'servers': list(self.servers.keys())
            }
        except Exception as e:
            logger.error(f"Failed to get server statistics: {str(e)}")
            return {
                'total_servers': 0,
                'active_servers': 0,
                'servers': []
            }