# coding: utf-8
# Date      : 2019-04-25
# PROJECT   : company
# File      : settings.py
from core.settings import BaseSettings


class CompanySettings(BaseSettings):
    PROJECT_NAME = 'company'
    REDIS_URL = 'redis://kylin:1291988293@xianyu.123nat.com:6379'
    REDIS_PROJECT_NAME = 'company'

    CONCURRENT_REQUESTS = 32
    CONCURRENT_WORDS = 32
    DEFAULT_TIMEOUT = 20
    DEFAULT_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Host': 'www.mingluji.com',
        'Referer': 'https://www.mingluji.com'
    }
    MYSQL_HOST = 'xianyu.123nat.com'
    MYSQL_DB = 'shunqi'
    MYSQL_USER = 'shunqi'
    MYSQL_PASSWORD = '1291988293'

    DOWNLOAD_DALEY = 0.5
    PROCESS_DALEY = 0.01
