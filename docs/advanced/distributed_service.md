## 核心函数

- `submit_function_task(delay: Union[int, None], daily_time: Union[str, None], function_type: str, timeout_processing: bool, task_name: str, func: Optional[Callable], priority: str, *args, **kwargs) -> Union[str, None]`

### !!!警告!!!

执行的代码导入库和使用其他函数必须包含在传入函数中出现和声明,否则序列化传输会出问题,服务端客户端必须存在一样的配置和文件

## 功能说明

采用三层架构：
1. **代理服务器**: 负责任务分发和负载均衡
2. **主服务器**: 实际执行任务的节点
3. **客户端**: 提交任务的终端

## 部署步骤

### 1. 启动代理服务器
在一个命令行中输入：
```bash
python -m task_scheduling.proxy_server