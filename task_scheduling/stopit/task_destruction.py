from typing import Dict, Any

from ..common.logging import logger


class TaskManager:
    def __init__(self):
        self.data: Dict[str, Any] = {}

    def add(self, instance: Any, key: str) -> None:
        """
        Add an instance and its key-value pair to the dictionary.

        :param instance: The instantiated class.
        :param key: A string used as the key in the dictionary.
        """
        self.data[key] = instance
        logger.info(f"Task '{key}' added")

    def force_stop(self, key: str) -> None:
        """
        Call the stop method of the corresponding instance using the key.

        :param key: A string, the key in the dictionary.
        """
        if key in self.data:
            instance = self.data[key]
            try:
                instance.stop()
                logger.warning(f"'{key}' stopped successfully")
            except Exception as error:
                logger.error(error)
        else:
            logger.warning(f"No task found with key '{key}', operation invalid")

    def force_stop_all(self) -> None:
        """
        Call the stop method of all instances in the dictionary.
        """
        for key, instance in self.data.items():
            try:
                instance.stop()
                logger.warning(f"'{key}' stopped successfully")
            except Exception as error:
                logger.error(error)

    def remove(self, key: str) -> None:
        """
        Remove the specified key-value pair from the dictionary.

        :param key: A string, the key in the dictionary.
        """
        if key in self.data:
            del self.data[key]
            logger.info(f"Task '{key}' removed")
        else:
            logger.warning(f"No task found with key '{key}', operation invalid")


# Create Manager instance
task_manager = TaskManager()
