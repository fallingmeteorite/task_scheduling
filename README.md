# How to use:

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

add_task(True, # 设置为True则启用检测超时检测,到达运行时间还没能结束的任务会被强制结束
         "task1", # 任务id,在线性任务中,同id的任务会排队执行,不同的id则会直接执行,异步也是一样的
         line_task,  # 要执行的函数，这里不用传入参数
         input_info       # 将函数需要的参数传入,没有限制
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
  
linetask.ban_task_id(task1)

add_task(True, 
         "task1", 
         line_task,  
         input_info      
         )
# 输出: Task task1 is banned and will be deleted
# asyntask, linetask都含有这个函数,并且使用方式相同
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
# 该代码将会删除排队任务中所有id为task1的任务
# asyntask, linetask都含有这个函数,并且使用方式相同             
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
# 该代码会强制结束正在运行的任务,注意!在读取或写入文件时使用该函数可能会造成文件损坏
# asyntask, linetask都含有这个函数,并且使用方式相同     
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
    result = linetaskk.get_task_result("task_id")
    if result is not None:
        print(f"Task result: {result}")
    time.sleep(0.5) 
    
# 输出: test
# asyntask, linetask都含有这个函数,并且使用方式相同
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
#输出:
# line queue size: 0, Running tasks count: 1
# ID: task1, Process Status: running, Elapsed Time: 0.00 seconds

#其他状态:
# ID: task1, Process Status: cancelled, Elapsed Time: 0.00 seconds
# ID: task1, Process Status: timeout, Elapsed Time: 0.00 seconds
# ID: task1, Process Status: failed, Elapsed Time: 0.00 seconds

# asyntask, linetask都含有这个函数,并且使用方式相同
```

# Reference libraries:

In order to facilitate subsequent modifications,

some files are placed directly into the folder instead of being installed via pip,

so the libraries used are specifically stated here:https://github.com/glenfant/stopit