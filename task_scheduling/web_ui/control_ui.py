# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import os
import time
import json
import threading

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from typing import Dict, Any

from ..common import logger, config
from ..manager import task_status_manager
from ..scheduler import kill_api, pause_api, resume_api


def format_tasks_info(tasks_dict: Dict[str, Dict[str, Any]]) -> str:
    """
    Format task information into a readable string with statistics.

    Args:
        tasks_dict: Dictionary containing task information with task_id as keys
                   and task details as values

    Returns:
        str: Formatted string containing task statistics and individual task details
    """
    # Initialize counters
    tasks_queue_size = 0
    running_tasks_count = 0
    failed_tasks_count = 0
    completed_tasks_count = 0

    # Process each task and collect formatted information
    formatted_tasks = []

    for task_id, task_info in tasks_dict.items():
        # Update counters based on task status
        status = task_info.get('status', 'unknown')

        if status == 'running':
            running_tasks_count += 1
        elif status == 'failed':
            failed_tasks_count += 1
        elif status == 'completed':
            completed_tasks_count += 1
        elif status in ['waiting', 'queuing']:
            tasks_queue_size += 1

        # Format individual task information
        task_str = _format_single_task(task_id, task_info)
        formatted_tasks.append(task_str)

    # Create statistics header
    stats_header = _create_stats_header(
        total_tasks=len(tasks_dict),
        queue_size=tasks_queue_size,
        running_count=running_tasks_count,
        failed_count=failed_tasks_count,
        completed_count=completed_tasks_count
    )

    # Combine header and task details
    output = stats_header
    if formatted_tasks:
        output += "\n\nTask Details:\n" + "\n".join(formatted_tasks)

    return output


def _format_single_task(task_id: str, task_info: Dict[str, Any]) -> str:
    """
    Format information for a single task.

    Args:
        task_id: Unique identifier for the task
        task_info: Dictionary containing task details

    Returns:
        str: Formatted string for the task
    """
    task_name = task_info.get('task_name', 'Unknown')
    status = task_info.get('status', 'unknown')
    task_type = task_info.get('task_type', 'Unknown')

    # Calculate elapsed time
    elapsed_time = _calculate_elapsed_time(task_info)

    # Format base task information
    task_str = (f"name: {task_name}, id: {task_id}, "
                f"status: {status}, elapsed time: {elapsed_time}, task_type: {task_type}")

    # Add error information if present
    error_info = task_info.get('error_info')
    if error_info is not None:
        task_str += f"\n  error_info: {error_info}"

    return task_str


def _calculate_elapsed_time(task_info: Dict[str, Any]) -> str:
    """
    Calculate and format the elapsed time for a task.

    Args:
        task_info: Dictionary containing task timing information

    Returns:
        str: Formatted elapsed time string
    """
    start_time = task_info.get('start_time')
    end_time = task_info.get('end_time')
    current_time = time.time()

    # Handle cases where start time is not available
    if start_time is None:
        return "N/A"

    # Calculate elapsed time based on task state
    if end_time is None:
        # Task is still running
        elapsed = current_time - start_time
        if elapsed > config.get("watch_dog_time", float('inf')):
            return "timeout"
    else:
        # Task has completed
        elapsed = end_time - start_time
        if elapsed > config.get("watch_dog_time", float('inf')):
            return "timeout"

    # Format the elapsed time
    if elapsed < 0.1:
        return f"{elapsed * 1000:.1f}ms"
    else:
        return f"{elapsed:.2f}s"


def _create_stats_header(total_tasks: int, queue_size: int, running_count: int,
                         failed_count: int, completed_count: int) -> str:
    """
    Create the statistics header for the task report.

    Args:
        total_tasks: Total number of tasks
        queue_size: Number of tasks in queue
        running_count: Number of running tasks
        failed_count: Number of failed tasks
        completed_count: Number of completed tasks

    Returns:
        str: Formatted statistics header
    """
    return (f"Task Statistics:\n"
            f"  Total Tasks: {total_tasks}\n"
            f"  Queued: {queue_size}\n"
            f"  Running: {running_count}\n"
            f"  Completed: {completed_count}\n"
            f"  Failed: {failed_count}")


def get_tasks_info() -> str:
    """
    Get formatted information about all tasks.

    Args:
        task_status_dict: Dictionary containing task status information

    Returns:
        str: Formatted task information output with statistics and details
    """
    return format_tasks_info(task_status_manager._task_status_dict)


def _terminate_task(task_id, task_type):
    """
    Terminate a task.

    Args:
        task_id (str): The ID of the task to terminate
        task_type (str): The type of the task

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        return kill_api(task_type, task_id)
    except:
        return False


def _pause_task(task_id, task_type):
    """
    Pause a task.

    Args:
        task_id (str): The ID of the task to pause
        task_type (str): The type of the task

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        return pause_api(task_type, task_id)
    except:
        return False


def _resume_task(task_id, task_type):
    """
    Resume a paused task.

    Args:
        task_id (str): The ID of the task to resume
        task_type (str): The type of the task

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        return resume_api(task_type, task_id)
    except:
        return False


def get_template_path():
    """Get the absolute path to the template file."""
    return os.path.join(os.path.dirname(__file__), 'ui.html')


def parse_task_info(tasks_info_str):
    """
    Parse the task info string into a structured dictionary.

    Args:
        tasks_info_str (str): Raw task information string

    Returns:
        dict: Structured task information with:
            - queue_size (int)
            - running_count (int)
            - failed_count (int)
            - completed_count (int)
            - tasks (list): List of task dictionaries
    """
    lines = tasks_info_str.split('\n')
    if not lines:
        return {
            'queue_size': 0,
            'running_count': 0,
            'failed_count': 0,
            'completed_count': 0,
            'tasks': []
        }

    # Parse summary line
    summary_line = lines[0]
    parts = summary_line.split(',')

    try:
        queue_size = int(parts[0].split(':')[1].strip())
        running_count = int(parts[1].split(':')[1].strip())
        failed_count = int(parts[2].split(':')[1].strip())
        completed_count = int(parts[3].split(':')[1].strip()) if len(parts) > 3 else 0
    except (IndexError, ValueError):
        queue_size = running_count = failed_count = completed_count = 0

    # Parse individual tasks
    tasks = []
    current_task = {}

    for line in lines[1:]:
        if line.startswith('name:'):
            if current_task:
                tasks.append(current_task)
                current_task = {}

            parts = line.split(',')
            current_task = {
                'name': parts[0].split(':')[1].strip(),
                'id': parts[1].split(':')[1].strip(),
                'status': parts[2].split(':')[1].strip().upper(),
                'type': "unknown",
                'duration': 0
            }

            # Extract task type and duration
            for part in parts[3:]:
                if 'task_type:' in part:
                    current_task['type'] = part.split(':')[1].strip()
                elif 'elapsed time:' in part:
                    try:
                        time_str = part.split(':')[1].strip().split()[0]
                        if time_str != "nan":
                            current_task['duration'] = float(time_str)
                    except (ValueError, IndexError):
                        pass

        elif line.startswith('error_info:'):
            current_task['error_info'] = line.split('error_info:')[1].strip()

    if current_task:
        tasks.append(current_task)

    return {
        'queue_size': queue_size,
        'running_count': running_count,
        'failed_count': failed_count,
        'completed_count': completed_count,
        'tasks': tasks
    }


class TaskControlHandler(BaseHTTPRequestHandler):
    """HTTP handler for task status information and control."""

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/':
            self._handle_root()
        elif parsed_path.path == '/tasks':
            self._handle_tasks()
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
            self.wfile.write(html.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, "Template file not found")

    def _handle_tasks(self):
        """Serve task information as JSON."""
        tasks_info = get_tasks_info()
        parsed_info = parse_task_info(tasks_info)

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(parsed_info).encode('utf-8'))

    def _handle_task_action(self, task_id, action):
        """Handle task control actions (terminate, pause, resume)."""
        try:
            # Get request body data
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                task_type = request_data.get('task_type', 'unknown')
            else:
                task_type = 'unknown'

            # Call corresponding API based on action
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

    def __init__(self, port=8000):
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Start the web UI in a daemon thread."""

        def run_server():
            self.server = HTTPServer(('', self.port), TaskControlHandler)
            logger.info(f"Task status UI available at http://localhost:{self.port}")
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


def start_task_status_ui(port=8000):
    """
    Start the task status web UI in a daemon thread.

    Args:
        port (int): Port number to serve the UI on (default: 8000)

    Returns:
        TaskStatusServer: The server instance which can be used to stop it manually
    """
    server = TaskStatusServer(port)
    server.start()
    return server
