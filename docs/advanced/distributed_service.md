## 分布式服务器(客户端/中转服务器/主服务器模式)

submit_function_task(delay: Union[int, None], daily_time: Union[str, None], function_type: str, timeout_processing:
bool, task_name: str, func: Optional[Callable], priority: str, *args, **kwargs) -> Union[str, None]

- 警告:

执行的代码需要的导入库和其他函数必须包含在传入函数中,否则序列化传输会出问题,服务端客户端必须存在一样的配置和文件

- 功能说明:

**代理服务器**: 负责任务分发和负载均衡

**主服务器**: 实际执行任务的节点

**客户端**: 提交任务的终端

- 部署步骤:

1.启动代理服务器

注意: 代理服务器只需要一个实例,可以在配置文件中修改ip

```bash
python -m task_scheduling.proxy_server
```

2.启动主服务器

注意: 最多可以开启999个主服务器,可以在配置文件中修改数量和ip

```bash
python -m task_scheduling.server
```

- 使用示例:

```python
def linear_task(input_info):
    import time
    while True:
        time.sleep(1)
        print(input_info)


if __name__ == "__main__":
    from task_scheduling.client import submit_function_task
    from task_scheduling.variable import *

    submit_function_task(
        None, None, FUNCTION_TYPE_IO, True, "linear_task",
        linear_task, priority_low, "running..."
    )
```
