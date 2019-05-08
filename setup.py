# coding: utf-8
# Date      : 2019/4/26
# Author    : kylin
# PROJECT   : aiocrawler
# File      : setup
from setuptools import setup, find_packages

setup(
    name="aiocrawler",
    version="1.20",
    keywords=["spider", "asynchronous", "crawler", "distributed"],
    author="kylin1020",
    author_email="kylin0521@gmail.com",
    description="The aiocrawler is a asynchronous/distributed web crawler/spider",
    url="https://github.com/kylin1020/aiocrawler",
    license="MIT",
    packages=find_packages(),
    package_data={"": ["*.py", "*.tmpl"]},
    install_requires=["aiohttp",
                      "aioredis",
                      "yarl",
                      "parsel",
                      "loguru",
                      "ujson",
                      "aiohttp-jinja2",
                      "aiohttp-session",
                      "aiojobs"
                      ],
    entry_points={"console_scripts": [
        "aiocrawler = aiocrawler.commands:main"
    ]},
    classifiers=[
        "Environment :: Web Environment",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7"
    ]
)
