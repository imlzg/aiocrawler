# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin
# PROJECT   : aiocrawler
# File      : user_agent_middleware
from aiocrawler import BaseSettings
from aiocrawler import Request
from aiocrawler.middlewares.middleware import BaseMiddleware


class UserAgentMiddleware(BaseMiddleware):
    def __init__(self, settings: BaseSettings):
        BaseMiddleware.__init__(self, settings)
        from fake_useragent import UserAgent
        self.__ua = UserAgent()

    def process_request(self, request: Request):
        request.headers['User-Agent'] = self.__ua.random
