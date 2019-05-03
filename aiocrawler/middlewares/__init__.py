from aiocrawler.middlewares.middleware import BaseDownloaderMiddleware
from aiocrawler.middlewares.allowed_codes_middleware import AllowedCodesMiddleware
from aiocrawler.middlewares.set_default_middleware import SetDefaultRequestMiddleware
from aiocrawler.middlewares.user_agent_middleware import UserAgentMiddleware


__all__ = [
    'BaseDownloaderMiddleware',
    'AllowedCodesMiddleware',
    'SetDefaultRequestMiddleware',
    'UserAgentMiddleware'
]
