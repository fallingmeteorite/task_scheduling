# Task Scheduling Library

一个功能强大的 Python 任务调度库，支持异步和同步任务执行，提供强大的任务管理和监控功能。

## ✨ 核心功能

> **⚠️ 实验性功能警告**
> 为测试功能，可能会出现异常和其他问题

- 🎯 **任务调度**: 支持异步代码和同步代码，相同名称的任务自动排队执行
- 📊 **任务管理**: 强大的任务状态监控和管理能力
- ⚡ **灵活控制**: 支持向执行代码发送（终止、暂停、恢复）命令
- ⏰ **超时处理**: 可为任务启用超时检测，长时间运行的任务会被强制终止
- 🔍 **状态查询**: 通过接口直接获取任务当前状态或者网页控制端
- 💤 **智能休眠**: 无任务时会自动休眠节省资源
- 🚀 **优先级管理**: 在任务过多时高优先级的任务会优先运行
- 📋 **结果获取**: 可以获取任务返回的运行结果
- 🚫 **任务禁用管理**: 可以在黑名单中添加任务名称，该名称的任务添加会被阻拦
- ❌ **队列任务取消**: 可以取消还在排队的同名称的所有任务
- 🧵 **线程级任务管理**: 灵活的任务结构管理
- 🌳 **任务树模式管理**: 当主任务结束，其他所有分支任务都会被销毁
- 🔗 **依赖型任务执行**: 依赖于主任务返回结果运行的函数将启动并运行
- 🔄 **任务重试**: 在对应的报错发生时重新尝试运行任务
- 🌐 **分布式管理**（实验性功能）: 可以使用客户端和服务端加中转服务器模式

## 🆕 对 NO GIL 的支持

使用 Python 3.14 以上的版本开启 `NO GIL` 即可使用，运行时会输出 `Free threaded is enabled`。

## 🚀 快速开始

### 基本使用示例

```python
import time
from task_scheduling.task_creation import task_creation
from task_scheduling.manager import task_scheduler
from task_scheduling.variable import *

def simple_task(message):
    for i in range(5):
        time.sleep(1)
        print(f"{message} - {i}")

if __name__ == "__main__":
    # 创建任务
    task_id = task_creation(
        None, None, FUNCTION_TYPE_IO, True, "simple_task",
        simple_task, priority_low, "Hello World"
    )
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        task_scheduler.shutdown_scheduler()