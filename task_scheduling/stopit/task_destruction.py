from typing import Dict, Any

from ..common.log_config import logger


class TaskManager:
    def __init__(self):
        self.data: Dict[str, Any] = {}

    def add(self, instance: Any, key: str) -> None:
        """
        添加一个实例及其键值对到字典中。

        :param instance: 实例化的类。
        :param key: 用作字典中键的字符串。
        """
        self.data[key] = instance

    def force_stop(self, key: str) -> None:
        """
        使用键调用字典中相应实例的 stop 方法。

        :param key: 用作字典中键的字符串。
        """
        if key in self.data:
            instance = self.data[key]
            try:
                instance.stop()
                logger.warning(f"'{key}' 停止成功")
            except Exception as error:
                logger.error(error)
        else:
            logger.warning(f"没有找到键为 '{key}' 的任务，操作无效")

    def force_stop_all(self) -> None:
        """
        调用字典中所有实例的 stop 方法。
        """
        for key, instance in self.data.items():
            try:
                instance.stop()
                logger.warning(f"'{key}' 停止成功")
            except Exception as error:
                logger.error(error)

    def remove(self, key: str) -> None:
        """
        从字典中移除指定的键值对。

        :param key: 用作字典中键的字符串。
        """
        if key in self.data:
            del self.data[key]
        else:
            logger.warning(f"没有找到键为 '{key}' 的任务，操作无效")

    def check(self, key: str) -> bool:
        """
        检查给定的键是否在字典中。

        :param key: 用作字典中键的字符串。
        :return: 如果键存在则返回 True，否则返回 False。
        """
        return key in self.data


# 创建 Manager 实例
task_manager = TaskManager()
