## introduce:

This python library is mainly used for task scheduling,
for example, there are a bunch of tasks here, the same type of tasks must be queued for execution,
and the tasks need strong management and monitoring

Asynchronous code and normal code are now supported,
specifically with event loops for asynchronous code

## Feature description

1.You can send a termination command to the execution code

2.You can enable timeout processing for a task, and terminate the task if it runs for too long

3.When a task fails to run, it can be added to the disabled list and will not be executed thereafter

4.You can directly obtain the current task status through the interface, such as executing, completed, error, and
timeout

5.Automatically hibernate when there are no tasks

!!! WARNING: If the task is running in a series of blocked tasks such as `time.sleep`, the task cannot be forcibly
terminated,
so use `await asyncio.sleep` for asynchronous tasks

## Installation

```
pip install task_scheduling
```

# Function introduction

### add_task(timeout_processing: bool, task_id: str, func: Callable, *args, **kwargs) -> None:

```

from task_scheduling import add_task

def line_task(input_info):
    time.sleep(3)
    return input_info
    
input_info = "test"

add_task(True, # Set to True to enable timeout detection, tasks that do not finish within the runtime will be forcibly terminated
         "task1", # Task ID, in linear tasks, tasks with the same ID will be queued, different IDs will be executed directly, the same applies to asynchronous tasks
         line_task,  # The function to be executed, parameters should not be passed here
         input_info       # Pass the parameters required by the function, no restrictions
         ) 

```

### ban_task_id(task_id: str) -> None:

```

from task_scheduling import asyntask, linetask, add_task

def task(input_info):
    time.sleep(3)
    return input_info
    
input_info = "test"

add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )
  
linetask.ban_task_id("task1")

add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )
# Output: Task task1 is banned and will be deleted
# Both asyntask and linetask contain this function, and the usage method is the same

```

### allow_task_id(task_id: str) -> None:

```
from task_scheduling import asyntask, linetask, add_task

def task(input_info):
    time.sleep(3)
    return input_info
    
input_info = "test"

add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )
  
linetask.ban_task_id("task1")

add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )
         
allow_task_id("task1")       
   
add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )      
# Removal of the ban on such tasks
# Both asyntask and linetask contain this function, and the usage method is the same
```

### cancel_all_queued_tasks_by_name(task_name: str) -> None:

```
from task_scheduling import asyntask, linetask, add_task
def task(input_info):
    time.sleep(3)
    return input_info
    
input_info = "test"

add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )
add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )
add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )
         
linetask.cancel_all_queued_tasks_by_name("task1")
# This code will delete all tasks with ID task1 in the queue
# Both asyntask and linetask contain this function, and the usage method is the same             
            
```

### force_stop_task(task_id: str) -> None:

```
from task_scheduling import asyntask, linetask, add_task
def task(input_info):
    time.sleep(3)
    return input_info
    
input_info = "test"

add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )
         
linetask.force_stop_task("task1")        
# This code will forcibly terminate the running task, note! Using this function during file reading or writing may cause file corruption
# Both asyntask and linetask contain this function, and the usage method is the same     
   
```

### get_task_result(task_id: str) -> Optional[Any]:

```
from task_scheduling import asyntask, linetask, add_task
def task(input_info):
    time.sleep(3)
    return input_info
    
input_info = "test"

add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )
         
while True:
    result = linetask.get_task_result("task1")
    if result is not None:
        print(f"Task result: {result}")
    time.sleep(0.5) 
    
# Output: test
# Both asyntask and linetask contain this function, and the usage method is the same

```

### get_all_queue_info(queue_type: str) -> str:

```
from task_scheduling import get_all_queue_info, add_task
def task(input_info):
    time.sleep(3)
    return input_info
    
input_info = "test"

add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )

print(get_all_queue_info("line"))
# Output:
# line queue size: 0, Running tasks count: 1
# ID: task1, Process Status: running, Elapsed Time: 0.00 seconds

# Other statuses:
# ID: task1, Process Status: cancelled, Elapsed Time: 0.00 seconds
# ID: task1, Process Status: timeout, Elapsed Time: 0.00 seconds
# ID: task1, Process Status: failed, Elapsed Time: 0.00 seconds

# Both asyntask and linetask contain this function, and the usage method is the same

```

配置文件文件存放于`common/config.yaml`

# Reference libraries:

In order to facilitate subsequent modifications,

some files are placed directly into the folder instead of being installed via pip,

so the libraries used are specifically stated here:https://github.com/glenfant/stopit