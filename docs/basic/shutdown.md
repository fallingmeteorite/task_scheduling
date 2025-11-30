## 正常关闭

shutdown_scheduler() -> None:

- 警告:

在关闭运行前必须执行该函数去结束和清理运行任务,在大型任务调度中建议在网页控制端先点击`Stop Adding Tasks`(停止任务添加)
防止进程任务初始化退出报错,如果没有使用,退出有概率出现报错,这是正常的

- 使用示例:

```python
from task_scheduling.manager import task_scheduler

# 要运行的代码...

task_scheduler.shutdown_scheduler()
```

## 异常关闭

abnormal_exit_cleanup() -> None:

- 警告:

这个必须在开启调度器前启用,只有在异常退出比如(代码报错,人为终止等场景会生效,如果是代码正常退出将不会生效),需要写在
`if __name__ == "__main__":`下面

- 使用示例:

```python
if __name__ == "__main__":
    from task_scheduling.task_creation import abnormal_exit_cleanup

    abnormal_exit_cleanup()
    # 你的运行代码
    ...
```