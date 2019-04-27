# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin
# PROJECT   : aiocrawler
# File      : user_agent_middleware
from aiocrawler.middlewares.middleware import BaseDownloaderMiddleware
from aiocrawler.settings import BaseSettings
from aiocrawler.request import Request


class UserAgentMiddleware(BaseDownloaderMiddleware):
    def __init__(self, settings: BaseSettings):
        BaseDownloaderMiddleware.__init__(self, settings)
        from fake_useragent import UserAgent
        self.__ua = UserAgent()

    def process_request(self, request: Request):
        request['headers']['User-Agent'] = self.__ua.random
