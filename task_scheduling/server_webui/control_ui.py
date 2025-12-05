# -*- coding: utf-8 -*-
# Author: fallingmeteorite
"""Web UI module for task monitoring and control.

This module provides a web-based user interface for monitoring task status,
controlling task execution, and managing task scheduling through HTTP endpoints.
"""
import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from task_scheduling.common import logger, config
from task_scheduling.manager import task_status_manager, task_scheduler
from task_scheduling.scheduler import kill_api, pause_api, resume_api

# Global variable to control task addition
_task_addition_enabled = True


def _stop_task_addition():
    """
    Stop task addition
    """
    try:
        global _task_addition_enabled
        _task_addition_enabled = False
        task_scheduler._stop_task_addition()
        logger.info("Task addition has been stopped")
        return True
    except Exception as e:
        logger.error(f"Failed to stop task addition: {str(e)}")
        return False


def _resume_task_addition():
    """
    Resume task addition
    """
    try:
        global _task_addition_enabled
        _task_addition_enabled = True
        task_scheduler._resume_task_addition()
        logger.info("Task addition has been resumed")
        return True
    except Exception as e:
        logger.error(f"Failed to resume task addition: {str(e)}")
        return False


def is_task_addition_enabled():
    """
    Check if task addition is enabled
    """
    return _task_addition_enabled


def get_task_addition_status():
    """
    Get task addition status information
    """
    return {
        'enabled': _task_addition_enabled,
        'status': 'enabled' if _task_addition_enabled else 'disabled'
    }


def format_tasks_info(tasks_dict):
    """
    Format task information into a readable string with statistics.
    """
    # Use internal helper to process task information
    tasks_queue_size = 0
    running_tasks_count = 0
    failed_tasks_count = 0
    completed_tasks_count = 0
    formatted_tasks = []

    for task_id, task_info in tasks_dict.items():
        status = task_info.get('status', 'unknown')

        # Count tasks by status
        if status == 'running':
            running_tasks_count += 1
        elif status == 'failed':
            failed_tasks_count += 1
        elif status == 'completed':
            completed_tasks_count += 1
        elif status in ['waiting', 'queuing']:
            tasks_queue_size += 1

        # Format individual task
        task_name = task_info.get('task_name', 'Unknown')
        task_type = task_info.get('task_type', 'Unknown')
        elapsed_time = _calculate_elapsed_time(task_info)
        error_info = task_info.get('error_info')

        task_str = (f"name: {task_name}, id: {task_id}, "
                    f"status: {status}, elapsed time: {elapsed_time}, task_type: {task_type}")

        if error_info is not None:
            task_str += f"\n  error_info: {error_info}"

        formatted_tasks.append(task_str)

    # Create statistics header
    total_tasks = len(tasks_dict)
    stats_header = (f"Task Statistics:\n"
                    f"  Total Tasks: {total_tasks}\n"
                    f"  Queued: {tasks_queue_size}\n"
                    f"  Running: {running_tasks_count}\n"
                    f"  Completed: {completed_tasks_count}\n"
                    f"  Failed: {failed_tasks_count}")

    output = stats_header
    if formatted_tasks:
        output += "\n\nTask Details:\n" + "\n".join(formatted_tasks)

    return output


def get_tasks_info():
    """
    Get task information as structured data.
    """
    tasks_dict = task_status_manager._task_status_dict

    # Calculate statistics
    tasks_queue_size = 0
    running_tasks_count = 0
    failed_tasks_count = 0
    completed_tasks_count = 0
    tasks = []

    for task_id, task_info in tasks_dict.items():
        status = task_info.get('status', 'unknown')

        # Count tasks by status
        if status == 'running':
            running_tasks_count += 1
        elif status == 'failed':
            failed_tasks_count += 1
        elif status == 'completed':
            completed_tasks_count += 1
        elif status in ['waiting', 'queuing']:
            tasks_queue_size += 1

        # Create task object
        task_obj = {
            'id': task_id,
            'name': task_info.get('task_name', 'Unknown'),
            'status': status.upper(),
            'type': task_info.get('task_type', 'Unknown'),
            'duration': _calculate_elapsed_time_seconds(task_info)
        }

        # Add error message if exists
        error_info = task_info.get('error_info')
        if error_info is not None:
            task_obj['error_info'] = str(error_info)

        tasks.append(task_obj)

    return {
        'queue_size': tasks_queue_size,
        'running_count': running_tasks_count,
        'failed_count': failed_tasks_count,
        'completed_count': completed_tasks_count,
        'tasks': tasks
    }


def _calculate_elapsed_time(task_info):
    """
    Calculate and format the elapsed time for a task.
    """
    start_time = task_info.get('start_time')
    end_time = task_info.get('end_time')
    current_time = time.time()

    if start_time is None:
        return "N/A"

    if end_time is None:
        elapsed = current_time - start_time
        if elapsed > config["watch_dog_time"]:
            return "timeout"
    else:
        elapsed = end_time - start_time
        if elapsed > config["watch_dog_time"]:
            return "timeout"

    if elapsed < 0.1:
        return f"{elapsed * 1000:.1f}ms"
    else:
        return f"{elapsed:.2f}s"


def _calculate_elapsed_time_seconds(task_info):
    """
    Calculate elapsed time in seconds for JSON output.
    """
    # Reuse the logic from _calculate_elapsed_time but return seconds
    start_time = task_info.get('start_time')
    end_time = task_info.get('end_time')
    current_time = time.time()

    if start_time is None:
        return 0

    if end_time is None:
        elapsed = current_time - start_time
    else:
        elapsed = end_time - start_time

    # Check Timeout
    if elapsed > config["watch_dog_time"]:
        return -1  # Special value indicates timeout

    return elapsed


def _create_stats_header(total_tasks, queue_size, running_count, failed_count, completed_count):
    """
    Create the statistics header for the task report.
    """
    return (f"Task Statistics:\n"
            f"  Total Tasks: {total_tasks}\n"
            f"  Queued: {queue_size}\n"
            f"  Running: {running_count}\n"
            f"  Completed: {completed_count}\n"
            f"  Failed: {failed_count}")


def _terminate_task(task_id, task_type):
    """
    Terminate a task.
    """
    try:
        return kill_api(task_type, task_id)
    except:
        return False


def _pause_task(task_id, task_type):
    """
    Pause a task.
    """
    try:
        return pause_api(task_type, task_id)
    except:
        return False


def _resume_task(task_id, task_type):
    """
    Resume a paused task.
    """
    try:
        return resume_api(task_type, task_id)
    except:
        return False


def get_template_path():
    """Get the absolute path to the template file."""
    return os.path.join(os.path.dirname(__file__), 'ui.html')


def is_port_available(host, port):
    """Check if a port is available on the specified host."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(host, start_port, max_attempts):
    """Find an available port starting from start_port on the specified host."""
    port = start_port
    attempts = 0

    while attempts < max_attempts:
        if is_port_available(host, port):
            return port
        port += 1
        attempts += 1

    raise RuntimeError(f"No available port found on {host} in range {start_port}-{start_port + max_attempts - 1}")


class TaskControlHandler(BaseHTTPRequestHandler):
    """HTTP handler for task status information and control."""

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/':
            self._handle_root()
        elif parsed_path.path == '/tasks':
            self._handle_tasks()
        elif parsed_path.path == '/task-addition-status':  # New status query endpoint
            self._handle_task_addition_status()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle POST requests for task control."""
        parsed_path = urlparse(self.path)
        path_parts = parsed_path.path.strip('/').split('/')

        if len(path_parts) >= 3 and path_parts[0] == 'tasks':
            task_id = path_parts[1]
            action = path_parts[2]
            self._handle_task_action(task_id, action)
        elif parsed_path.path == '/toggle-task-addition':  # New toggle endpoint
            self._handle_toggle_task_addition()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_root(self):
        """Serve the main HTML page."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        try:
            with open(get_template_path(), 'r', encoding='utf-8') as f:
                html = f.read()
            try:
                self.wfile.write(html.encode('utf-8'))
            except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
                # The client has disconnected. This is normal and does not need to be recorded as an error.
                logger.debug("Client disconnected before receiving response")

        except FileNotFoundError:
            self.send_error(404, "Template file not found")

    def _handle_tasks(self):
        """Serve task information as JSON."""
        parsed_info = get_tasks_info()

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        try:
            self.wfile.write(json.dumps(parsed_info).encode('utf-8'))
        except ConnectionAbortedError:
            pass

    def _handle_task_addition_status(self):
        """Handle task addition status query"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        try:
            status_info = get_task_addition_status()
            self.wfile.write(json.dumps(status_info).encode('utf-8'))
        except ConnectionAbortedError:
            pass

    def _handle_toggle_task_addition(self):
        """Handle task addition status toggle"""
        try:
            global _task_addition_enabled
            if _task_addition_enabled:
                result = _stop_task_addition()
                action = 'stopped'
            else:
                result = _resume_task_addition()
                action = 'resumed'

            if result:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': f'Task addition {action} successfully',
                    'enabled': _task_addition_enabled
                }).encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': f'Failed to {action} task addition'
                }).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'message': f'Internal server error: {str(e)}'
            }).encode('utf-8'))

    def _handle_task_action(self, task_id, action):
        """Handle task control actions (terminate, pause, resume)."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                task_type = request_data.get('task_type', 'unknown')
            else:
                task_type = 'unknown'

            result = None
            if action == 'terminate':
                result = _terminate_task(task_id, task_type)
            elif action == 'pause':
                result = _pause_task(task_id, task_type)
            elif action == 'resume':
                result = _resume_task(task_id, task_type)
            else:
                self.send_response(404)
                self.end_headers()
                return

            if result:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': f'Task {task_id} {action}d successfully',
                    'task_type': task_type
                }).encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': f'Failed to {action} task {task_id}'
                }).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'message': f'Internal server error: {str(e)}'
            }).encode('utf-8'))

    def log_message(self, format, *args):
        """Override to disable logging."""
        pass


class TaskStatusServer:
    """Server for displaying task status information."""

    def __init__(self):
        """
        Initialize the task status server.
        """
        self.host = config["webui_host"]
        self.port = config["webui_port"]
        self.max_port_attempts = config["max_port_attempts"]
        self.actual_port = None  # Store the actual port used
        self.server = None
        self.thread = None

    def start(self):
        """Start the web UI in a daemon thread."""

        def run_server():
            """Start Service"""
            # Find available port with max attempts limit
            self.actual_port = find_available_port(self.host, self.port, self.max_port_attempts)
            self.server = HTTPServer((self.host, self.actual_port), TaskControlHandler)

            logger.info(f"Task status UI available at http://{self.host}:{self.actual_port}")

            self.server.serve_forever()

        self.thread = threading.Thread(target=run_server)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the web server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=1)

    def get_actual_port(self):
        """Get the actual port used by the server."""
        return self.actual_port if self.actual_port else self.port


def start_task_status_ui(host='', port=7999, max_port_attempts=100):
    """
    Start the task status web UI in a daemon thread.

    Args:
        host (str): Host to bind to. Default '' means all interfaces.
                    Use '127.0.0.1' for localhost only.
                    Use '0.0.0.0' for all interfaces.
        port (int): Starting port number, will auto-increment if occupied
        max_port_attempts (int): Maximum number of port attempts when default port is occupied

    Returns:
        TaskStatusServer: The server instance with actual port information
    """
    server = TaskStatusServer()
    server.port = port  # Port in override configuration
    server.max_port_attempts = max_port_attempts
    server.start()
    return server
