# coding: utf-8
# Date      : 2019-04-28
# PROJECT   : credit
# File      : settings.py
from aiocrawler import BaseSettings
from middlewares import CreditMiddleware


class CreditSettings(BaseSettings):
    PROJECT_NAME = 'credit'

    """
    If you use the redis server as the scheduler, the REDIS_URL must be configured.
    """
    # REDIS_URL = 'redis://kylin:1291988293@xianyu.123nat.com:6379'
    REDIS_PROJECT_NAME = 'credit'

    CONCURRENT_REQUESTS = 32
    CONCURRENT_WORDS = 32
    DEFAULT_TIMEOUT = 20
    DEFAULT_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN',
    }

    DOWNLOAD_DALEY = 0.5
    PROCESS_DALEY = 0.01
    MIDDLEWARES = [
        (CreditMiddleware, 300),

    ]

    MONGO_HOST = 'localhost'
    MONGO_PORT = 27017
    MONGO_USER = 'kylin'
    MONGO_PASSWORD = '1291988293'
