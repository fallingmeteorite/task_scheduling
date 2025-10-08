from setuptools import setup, find_packages

setup(
    name="task_scheduling",
    version="4.0.1",
    description="It is mainly used for task scheduling",
    author="fallingmeteorite",
    author_email="2327667836@qq.com",
    license="MIT License",
    url="https://github.com/fallingmeteorite/task_scheduling",

    python_requires=">=3.8",

    packages=find_packages(),
    install_requires=[
        "loguru",
        "pyyaml"
    ],
    project_urls={
        "Bug Tracker": "https://github.com/fallingmeteorite/task_scheduling/issues",
    },
)