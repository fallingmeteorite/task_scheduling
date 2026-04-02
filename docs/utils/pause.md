## 任务暂停恢复

line_tracer(pause_indicator: bool) -> None:

- 警告:

该函数适合双平台使用,但是性能损耗极其高,所以非必要不推荐使用,`Windows`
系统可以直接使用库自带的暂停api,使用时候要先使用`create_shared_flag`
函数获取可多进程访问的布尔值!

- 参数说明:

**pause_indicator**: 暂停任务指标

- 使用示例:

```python
import time


def main():
    frist = time.time()
    for i in range(100):
        time.sleep(1)
        print("running")
    end = time.time()
    print(f"{end - frist:.10f}")


def test(flag):
    time.sleep(4)
    flag.value = True
    time.sleep(4)
    flag.value = False


from task_scheduling.utils import line_tracer, create_shared_flag
import threading

if __name__ == "__main__":
    flag = create_shared_flag()
    flag.value = False
    threading.Thread(target=test, args=(flag,), daemon=True).start()
    with line_tracer(flag):
        main()

```



