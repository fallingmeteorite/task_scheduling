# -*- coding: utf-8 -*-
# Author: fallingmeteorite
import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from ..scheduler import io_asyncio_task, io_liner_task, cpu_liner_task, cpu_asyncio_task, timer_task
from ..common import logger


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
        from ..manager import get_tasks_info  # Import your task info function
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
                result = self._terminate_task(task_id, task_type)
            elif action == 'pause':
                result = self._pause_task(task_id, task_type)
            elif action == 'resume':
                result = self._resume_task(task_id, task_type)
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

    def _terminate_task(self, task_id, task_type):
        """
        Terminate a task.

        Args:
            task_id (str): The ID of the task to terminate
            task_type (str): The type of the task

        Returns:
            bool: True if successful, False otherwise
        """
        try:

            if task_type == "cpu_liner_task":
                cpu_liner_task.force_stop_task(task_id)
            elif task_type == "cpu_asyncio_task":
                cpu_asyncio_task.force_stop_task(task_id)
            elif task_type == "io_liner_task":
                io_liner_task.force_stop_task(task_id)
            elif task_type == "io_asyncio_task":
                io_asyncio_task.force_stop_task(task_id)
            elif task_type == "timer_task":
                timer_task.force_stop_task(task_id)

            # Temporary return success for testing
            return True
        except:
            return False

    def _pause_task(self, task_id, task_type):
        """
        Pause a task.

        Args:
            task_id (str): The ID of the task to pause
            task_type (str): The type of the task

        Returns:
            bool: True if successful, False otherwise
        """
        try:

            if task_type == "cpu_liner_task":
                cpu_liner_task.pause_and_resume_task(task_id, "pause")
            elif task_type == "cpu_asyncio_task":
                cpu_asyncio_task.pause_and_resume_task(task_id, "pause")
            elif task_type == "io_liner_task":
                io_liner_task.pause_and_resume_task(task_id, "pause")
            elif task_type == "io_asyncio_task":
                io_asyncio_task.pause_and_resume_task(task_id, "pause")
            elif task_type == "timer_task":
                timer_task.pause_and_resume_task(task_id, "pause")

            # Temporary return success for testing
            return True

        except:
            return False

    def _resume_task(self, task_id, task_type):
        """
        Resume a paused task.

        Args:
            task_id (str): The ID of the task to resume
            task_type (str): The type of the task

        Returns:
            bool: True if successful, False otherwise
        """
        try:

            if task_type == "cpu_liner_task":
                cpu_liner_task.pause_and_resume_task(task_id, "resume")
            elif task_type == "cpu_asyncio_task":
                cpu_asyncio_task.pause_and_resume_task(task_id, "resume")
            elif task_type == "io_liner_task":
                io_liner_task.pause_and_resume_task(task_id, "resume")
            elif task_type == "io_asyncio_task":
                io_asyncio_task.pause_and_resume_task(task_id, "resume")
            elif task_type == "timer_task":
                timer_task.pause_and_resume_task(task_id, "resume")

            # Temporary return success for testing
            return True

        except:
            return False

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
