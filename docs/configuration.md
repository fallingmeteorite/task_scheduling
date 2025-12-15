## 默认配置文件存放位置

文件存储在: `task_scheduling/config/config_gil.yaml` 或 `task_scheduling/config/config_no_gil.yaml`

- 警告:

`no_gil`和`gil`在`io_liner_task``timer_task`有区别

## 配置参数说明

**任务数量限制**

- `cpu_asyncio_task: 30` - CPU 密集型异步任务可以运行的最大数量
- `io_asyncio_task: 20` - IO 密集型异步任务单个事件循环的运行最大任务数
- `cpu_liner_task: 30` - CPU 密集型线性任务中运行最大任务数
- `io_liner_task: 1000` (`no_gil: 60`) - IO 密集型线性任务中运行最大任务数
- `timer_task: 1000` (`no_gil: 60`) - 定时器可执行最多任务数

**系统配置**

- `maximum_event_loop: 1000` - IO 密集型异步任务调度器事件循环最大创建数量
- `max_idle_time: 300` - 当多长时间没有任务时,关闭该任务调度器(秒)
- `watch_dog_time: 300` - 当任务运行多久而未完成时,尝试强制结束(秒)

**存储配置**

- `maximum_task_info_storage: 2000` - 任务状态存储器中最大存储任务数
- `maximum_result_storage: 1000` - 单个调度器最大储存返回结果数量
- `maximum_result_time_storage: 20` - 当任务返回结果多久没有被取走会被清理(秒)

**IP配置**

- `proxy_port: 127.0.0.1` - 代理服务器host
- `proxy_host: 7999` - 代理服务器端口
- `server_host: 127.0.0.1` - 主服务器host
- `server_port: 8000` - 主服务器端口
- `webui_host: 127.0.0.1` - 网页控制端服务器host
- `webui_port: 8100` - 网页控制端服务器端口
- `get_host: 127.0.0.1` - 结果储存服务器host
- `get_port: 8200` - 结果储存服务器端口
- `control_host: 127.0.0.1` - 控制服务器host
- `control_port: 8201` - 控制服务器端口
- `max_port_attempts: 100` - 主服务器和网页控制端服务器最大存在数量

**其他配置**

- `exception_thrown: false` - 是否应该抛出异常而不捕获以便定位错误
- `network_storage_results: false` - 是否启用结果储存服务器

## 临时更新配置参数(热加载)

update_config(key: str, value: Any) -> Any

- 警告:

请放在`if __name__ == "__main__":`前面,部分参数没法在调度器启动后修改并生效,或者在导入其他部分之前使用

- 参数说明:

**key**: 键

**value**: 值

返回值: True或者报错信息

- 使用示例:

```python
from task_scheduling.common import update_config

# 更新配置
update_config("max_idle_time", 600)

if __name__ == "__main__":
    # 你的运行代码
    ...
```

## 临时更改加载的配置文件(热加载)

set_config_directory(config_dir: str) -> bool:

- 警告:

请放在`if __name__ == "__main__":`前面,部分参数没法在启动后修改并生效

- 参数说明:

**config_dir**: 加载文件路径

**返回**: True或False

- 使用示例:

```python
from task_scheduling.common import set_config_directory

# 更新配置
set_config_directory("文件位置")

if __name__ == "__main__":
    # 你的运行代码
    ...
```

## 日志等级设置

set_log_level(level: str):

- 参数说明:

**level**: 日志等级比如`INFO`/`DEBUG`高于的等级将会输出

- 使用示例:

```python
from task_scheduling.common import set_log_level

set_log_level("DEBUG")

if __name__ == "__main__":
    # 你的运行代码
    ...
```