## 非阻塞睡眠

interruptible_sleep(seconds: Union[float, int]) -> None:

- 警告:

这个参数适合比如睡眠100秒之类的,有微小的性能损耗,如果不是必要或者睡眠时间很短不建议使用

- 参数说明:

**seconds**: 睡眠多久(秒)

- 使用示例:

```python
from task_scheduling.utils import interruptible_sleep


def linear_task(input_info):
    for i in range(10):
        interruptible_sleep(1)
        print(f"Linear task: {input_info} - {i}")
```



