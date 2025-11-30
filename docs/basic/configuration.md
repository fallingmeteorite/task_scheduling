## 配置文件位置

文件存储在: `task_scheduling/config/config_gil.yaml` 或 `config_no_gil.yaml`

### !!!警告!!!

`no_gil`和`gil`在`io_liner_task``timer_task`有区别

## 配置参数说明

### 任务数量限制

- `cpu_asyncio_task: 30` - 同名称的 CPU 密集型异步任务可以运行的最大数量
- `io_asyncio_task: 20` - IO 密集型异步任务单个事件循环的运行最大任务数
- `cpu_liner_task: 30` - CPU 密集型线性任务中运行最大任务数
- `io_liner_task: 1000` (`no_gil: 60`) - IO 密集型线性任务中运行最大任务数
- `timer_task: 1000` (`no_gil: 60`) - 定时器执行最多任务数

### 系统配置

- `maximum_event_loop: 100` - 事件循环最大创建数量
- `max_idle_time: 300` - 当多长时间没有任务时,关闭任务调度器(秒)
- `watch_dog_time: 300` - 当任务运行多久而未完成时,强制结束(秒)

### 存储配置

- `maximum_task_info_storage: 2000` - 任务状态存储器中最大存储任务数
- `status_check_interval: 300` - 多久检查存储器中任务状态是否正确(秒)
- `maximum_result_storage: 1000` - 单个调度器最大储存返回结果数量
- `maximum_result_time_storage: 300` - 多久清理一次返回结果储存(秒)

### 其他配置

- `exception_thrown: false` - 是否应该抛出异常而不捕获以便定位错误
- `network_storage_results: false` - 是否启用结果储存服务器

## 临时更新配置参数(热加载)

- `update_config(key: str, value: Any) -> Any`

### !!!警告!!!

请放在`if __name__ == "__main__":`前面,部分参数没法在启动后修改并生效

### 参数说明:

**key**: 键
**value**: 值

返回值: True或者报错信息

### 使用示例:

```python
from task_scheduling.common import update_config

# 更新配置
update_config("max_idle_time", 600)

if __name__ == "__main__":
    # 你的运行代码
    ...