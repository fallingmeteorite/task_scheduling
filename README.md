# Task Scheduling

一个强大的 Python 任务调度库，提供灵活的任务管理和调度功能。

## 特性

- 🚀 简单易用的任务创建和管理
- ⏰ 灵活的定时调度策略
- 🔄 支持任务重试和依赖管理
- 🌐 内置 Web 控制界面
- 🧵 支持线程级任务执行
- 🌳 任务树模式支持
- 🔗 分布式服务支持
- 📊 实时状态监控和结果查询

## 快速开始

### 安装

```bash
pip install task_scheduling
```

### 基本使用

```python
import time
from task_scheduling.variable import *
from task_scheduling.utils import interruptible_sleep


def linear_task(input_info):
    for i in range(10):
        interruptible_sleep(1)
        print(f"Linear task: {input_info} - {i}")


if __name__ == "__main__":
    from task_scheduling.task_creation import task_creation
    from task_scheduling.manager import task_scheduler

    task_id1 = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "linear_task",
        linear_task, priority_low, "Hello Linear"
    )

    while True:
        try:
            time.sleep(0.1)
        except KeyboardInterrupt:
            task_scheduler.shutdown_scheduler()
```

### 文档

详细使用说明和完整功能请查看:
https://fallingmeteorite.github.io/task_scheduling/

### 许可证

MIT License

### 贡献

欢迎提交 Issue 和 Pull Request！