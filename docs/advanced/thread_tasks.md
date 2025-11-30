### !!!警告!!!

!!!该功能只支持CPU密集型线性任务!!!

### 功能说明:

`main_task`中前三位接受参数必须为`share_info`, `_sharedtaskdict`, `task_signal_transmission`(
如果开启了该功能,正常任务也可以使用,只需要不传入前面所说的三个参数)

`@wait_branch_thread_ended`必须放在main_task上面，防止主线程结束,分支线程还没运行完导致错误

`other_task`为需要运行的分支线程,上面必须添加`@branch_thread_control`装饰器来控制和监视

`@branch_thread_control`装饰器接收参数`share_info`, `_sharedtaskdict`, `timeout_processing`, `task_name`

`task_name`必须是唯一不重复的,用于获取其他分支线程的task_id(使用`_sharedtaskdict.read(task_name)`
获取task_id去终止，暂停或恢复)名字将按照`main_task_name|task_name`显示

使用`threading.Thread`语句必须添加`daemon=True`将线程设置为守护线程(
没有添加会让关闭操作时间增加,反正主线程结束,会强制终止所有分支线程)

所有的分支线程都可以在网页端查看到运行状态(开启网页端请使用`start_task_status_ui()`)

### 控制方式

在主线程内使用:

```python
task_signal_transmission[_sharedtaskdict.read(task_name)] = ["action"]