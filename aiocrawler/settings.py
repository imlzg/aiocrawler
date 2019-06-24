# coding: utf-8


class BaseSettings:

    PROJECT_NAME = None

    ENABLE_REDIS_SETTINGS = False
    REDIS_URL = None
    REDIS_PROJECT_NAME = None
    DISABLE_REDIS = False

    MONGO_HOST = None
    MONGO_PORT = 27017
    MONGO_DB = None
    MONGO_USER = None
    MONGO_PASSWORD = None

    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = None
    MYSQL_DB = None

    CONCURRENT_REQUESTS = 32
    CONCURRENT_WORDS = 8
    DEFAULT_TIMEOUT = 30
    DEFAULT_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN',
    }

    DOWNLOAD_DALEY = 0
    PROCESS_DALEY = 0.2

    AIOJOBS_LIMIT = 10000
    AIOJOBS_CLOSED_TIMEOUT = 0.1

    DASHBOARD_USER = None
    DASHBOARD_PASSWORD = None

    ALLOWED_CODES = []

    MIDDLEWARES = []

    DEFAULT_MIDDLEWARES = {
        'SetDefaultMiddleware': 0,
        'UserAgentMiddleware': 1,
    }

    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
