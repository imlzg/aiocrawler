# coding: utf-8
# Date      : 2019/4/26
# Author    : kylin
# PROJECT   : aiocrawler
# File      : setup
from setuptools import setup, find_packages


setup(
    name="aiocrawler",
    version="1.0",
    keywords=["spider", "crawler", "async"],
    description="Aiocrawler is a asynchronous web crawler",
    license="MIT",
    author="kylin1020",
    author_email="kylin1020@google.com",
    url="https://github.com/kylin1020/aiocrawler",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["aiohttp", "aioredis", "yarl", "loguru", "parsel"],
    entry_points={'console_scripts': [
        'aiocrawler = aiocrawler.core.aiocrawler:commands',
    ]},
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Indexing",
        "Topic :: Utilities",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        ]
)

