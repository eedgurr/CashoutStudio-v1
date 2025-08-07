from setuptools import setup, find_packages

setup(
    name="cashout-studio-v1",
    version="1.0.0",
    description="Offline AI tuning canvas + Web3 signatures with ECU support",
    author="eedgurr",
    packages=find_packages(),
    install_requires=[
        "pyserial>=3.5",
        "python-can>=4.2.0",
        "dataclasses-json>=0.5.7",
        "pydantic>=2.0.0",
        "loguru>=0.7.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "cashout-studio=cashout_studio.cli:main",
        ],
    },
)