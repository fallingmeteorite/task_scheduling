# Cache dictionaries
cache_dict = {}


# Initialize the dictionary function
def init_dict():
    """
    Initialize the dictionary by reading from a JSON file.

    Returns:
        Dict: Dictionary containing task types.
    """
    try:
        with open(f"{get_package_directory()}/task_type.json", 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


# Append functions
def append_to_dict(task_name: str, function_type: str) -> None:
    """
    Append a task and its type to the dictionary and update the JSON file.

    Args:
        task_name (str): The name of the task.
        function_type (str): The type of the function.
    """
    global cache_dict
    tasks_dict = init_dict()
    if task_name in tasks_dict:
        logger.info(f"The name of the task {task_name} already exists, update its function type.")
    else:
        logger.info(f"The name of the task {task_name} it does not exist, add a new task.")
    tasks_dict[task_name] = function_type
    with open(f"{get_package_directory()}/task_type.json", 'w') as file:
        json.dump(tasks_dict, file, indent=4)
    cache_dict[task_name] = function_type
    logger.info(f"The task name has been added {task_name} and its function type {function_type}.")


# Read the function
def read_from_dict(task_name: str) -> Optional[str]:
    """
    Read the function type for a specified task name from the cache or JSON file.

    Args:
        task_name (str): The name of the task.

    Returns:
        Optional[str]: The function type if the task name exists; otherwise, None.
    """
    global cache_dict
    if task_name in cache_dict:
        logger.info(f"Returns the task name from the cache {task_name} the type of function.")
        return cache_dict[task_name]
    else:
        logger.info(f"The name of the task {task_name} not in the cache, read from the file.")
        tasks_dict = init_dict()
        cache_dict = tasks_dict  # Update the cache
        return tasks_dict.get(task_name, None)




# 示例
append_to_dict('task1', 'type1')
append_to_dict('task2', 'type2')

print(read_from_dict('task1'))  # 输出: type1
print(read_from_dict('task3'))  # 输出: None