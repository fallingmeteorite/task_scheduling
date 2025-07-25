from setuptools import setup, find_packages

setup(
    name="task_scheduling",
    version="2.3.1",
    description="It is mainly used for task scheduling",
    author="fallingmeteorite",
    author_email="2327667836@qq.com",
    license="MIT License",
    url="https://github.com/fallingmeteorite/task_scheduling",
    packages=find_packages(),
    install_requires=[
        "loguru",
        "pyyaml",
        "psutil"
    ],
    project_urls={
        "Bug Tracker": "https://github.com/fallingmeteorite/task_scheduling/issues",
    },
)
