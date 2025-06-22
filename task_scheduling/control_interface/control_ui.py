import os
from ..common import logger
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import json


def get_template_path():
    """Get the absolute path to the template file"""
    return os.path.join(os.path.dirname(__file__), 'ui.html')


def parse_task_info(tasks_info_str):
    """Parse the task info string into a structured dictionary"""
    lines = tasks_info_str.split('\n')
    if not lines:
        return {
            'queue_size': 0,
            'running_count': 0,
            'failed_count': 0,
            'completed_count': 0,
            'tasks': []
        }

    summary_line = lines[0]
    parts = summary_line.split(',')

    try:
        queue_size = int(parts[0].split(':')[1].strip())
        running_count = int(parts[1].split(':')[1].strip())
        failed_count = int(parts[2].split(':')[1].strip())
        completed_count = int(parts[3].split(':')[1].strip()) if len(parts) > 3 else 0
    except (IndexError, ValueError):
        queue_size, running_count, failed_count, completed_count = 0, 0, 0, 0

    tasks = []
    current_task = {}

    for line in lines[1:]:
        if line.startswith('name:'):
            if current_task:
                tasks.append(current_task)
                current_task = {}

            parts = line.split(',')
            current_task['name'] = parts[0].split(':')[1].strip()
            current_task['id'] = parts[1].split(':')[1].strip()
            current_task['status'] = parts[2].split(':')[1].strip().upper()

            # Extract task type and duration
            current_task['type'] = "unknown"
            current_task['duration'] = 0
            for part in parts[3:]:
                if 'task_type:' in part:
                    current_task['type'] = part.split(':')[1].strip()
                elif 'elapsed time:' in part:
                    try:
                        current_task['duration'] = float(part.split(':')[1].strip().split()[0])
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


class SilentTaskStatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            try:
                with open(get_template_path(), 'r', encoding='utf-8') as f:
                    html = f.read()
                self.wfile.write(html.encode('utf-8'))
            except FileNotFoundError:
                self.send_error(404, "Template file not found")

        elif parsed_path.path == '/tasks':
            from .queue_info_display import get_tasks_info  # Import your task info function
            tasks_info = get_tasks_info()
            parsed_info = parse_task_info(tasks_info)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write(json.dumps(parsed_info).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Override to disable logging"""
        pass


class TaskStatusServer:
    def __init__(self, port=8000):
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Start the web UI in a daemon thread"""

        def run_server():
            self.server = HTTPServer(('', self.port), SilentTaskStatusHandler)
            logger.info(f"Task status UI available at http://localhost:{self.port}")
            self.server.serve_forever()

        self.thread = threading.Thread(target=run_server)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the web server"""
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