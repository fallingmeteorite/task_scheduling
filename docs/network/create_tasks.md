## 任务创建函数

submit_task(delay: int or None, daily_time: str or None, function_type: str, timeout_processing: bool, task_name:
str, func: Callable, *args, **kwargs) -> str or None

- 警告:

`Windows`,`Linux`,`Mac`在多进程中都统一使用`spawn`

IO异步任务中将不会阻拦同名任务执行,将提交后交给事件循环管理,其他任务中的同名任务都会排队执行(
可以在工具一栏找到随机名字来绕过该限制,前提是该任务执行的不是读写等,不能多线程操作的行为)

使用网络功能时候必须将配置文件中的`network_storage_results`改为`true`,所有代码的使用函数或者导入库都必须写在提交函数
内部装饰器也是一样的,不然反序列化和运行会出现问题

- 参数说明:

**delay**: 延迟执行时间(秒),用于定时任务(不使用填写None,和下面参数二选一)

**daily_time**: 每日执行时间,格式"HH:MM",用于定时任务,使用24小时制(不使用填写None,和上面参数二选一)

**function_type**: 函数类型 (`FUNCTION_TYPE_IO`, `FUNCTION_TYPE_CPU`, `FUNCTION_TYPE_TIMER`)

**timeout_processing**: 是否启用超时终止 (`True`, `False`)

**task_name**: 任务名称,相同名称的任务会排队执行

**func**: 要执行的函数

**priority**: 任务优先级 (`priority_low`, `priority_high`)

**args, kwargs**: 函数参数

**返回**: 任务ID字符串

- 部署步骤:

1.启动代理服务器

注意: 代理服务器只需要一个实例,可以在配置文件中修改ip

```bash
python -m task_scheduling.proxy_server
```

2.启动主服务器

注意: 最多可以开启100个主服务器,可以在配置文件中修改数量和ip

```bash
python -m task_scheduling.server
```

- 使用示例:

```python
def linear_task(input_info):
    from task_scheduling.utils import interruptible_sleep
    for i in range(10):
        interruptible_sleep(1)
        print(f"Linear task: {input_info} - {i}")


async def async_task(input_info):
    import asyncio
    for i in range(10):
        await asyncio.sleep(1)
        print(f"Async task: {input_info} - {i}")


if __name__ == "__main__":
    from task_scheduling.client import submit_task
    from task_scheduling.variable import *

    task_id1 = submit_task(
        None, None, FUNCTION_TYPE_IO, True, "linear_task",
        linear_task, priority_low, "Hello Linear"
    )

    task_id2 = submit_task(
        None, None, FUNCTION_TYPE_IO, True, "async_task",
        async_task, priority_low, "Hello Async"
    )
```