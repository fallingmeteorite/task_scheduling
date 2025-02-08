import multiprocessing
#import psutil
import time
import asyncio


class FunctionRunner:
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.process = None
        self.process_info = None
        self.cpu_usage_history = []
        self.memory_usage_history = []

    def run(self):
        self.process = multiprocessing.Process(target=self._run_function)
        self.process.start()
        self.process_info = psutil.Process(self.process.pid)
        self._monitor_process()

    def _run_function(self):
        if asyncio.iscoroutinefunction(self.func):
            asyncio.run(self.func(*self.args, **self.kwargs))
        else:
            self.func(*self.args, **self.kwargs)

    def _monitor_process(self):
        try:
            while self.process.is_alive():
                # CPU usage
                cpu_usage = self.process_info.cpu_percent(interval=1)
                self.cpu_usage_history.append(cpu_usage)

                # Memory usage
                memory_usage = self.process_info.memory_info().rss / (1024 * 1024)
                self.memory_usage_history.append(memory_usage)

                print(f"CPU Usage: {cpu_usage}%")
                print(f"Memory Usage: {memory_usage:.2f} MB")

                time.sleep(1)
        except psutil.NoSuchProcess:
            pass
        finally:
            self.process.join()
            self._analyze_task_type()

    def _analyze_task_type(self):
        if not self.cpu_usage_history or not self.memory_usage_history:
            print("No data to analyze.")
            return

        avg_cpu_usage = sum(self.cpu_usage_history) / len(self.cpu_usage_history)
        avg_memory_usage = sum(self.memory_usage_history) / len(self.memory_usage_history)

        print(f"Average CPU Usage: {avg_cpu_usage}%")
        print(f"Average Memory Usage: {avg_memory_usage:.2f} MB")

        # Heuristic to determine task type
        if avg_cpu_usage > 50:
            print("Task is likely CPU-intensive.")
        else:
            print("Task is likely I/O-intensive.")


# Example usage
def example_cpu_intensive_function():
    for i in range(1000000):
        _ = i * i


async def example_io_intensive_function():
    for i in range(5):
        with open(f"temp_file_{i}.txt", "w") as f:
            f.write("Hello, World!" * 1000000)
        time.sleep(1)


if __name__ == "__main__":
    cpu_runner = FunctionRunner(example_cpu_intensive_function)
    cpu_runner.run()

    io_runner = FunctionRunner(example_io_intensive_function)
    io_runner.run()