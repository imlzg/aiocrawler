# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin
# PROJECT   : aiocrawler
# File      : set_default_middleware
from core.settings import BaseSettings
from core.request import Request
from core.middlewares.middleware import BaseDownloaderMiddleware


class SetDefaultRequestMiddleware(BaseDownloaderMiddleware):
    def __init__(self, settings: BaseSettings):
        BaseDownloaderMiddleware.__init__(self, settings)

    def process_request(self, request: Request):
        if request['timeout'] is None:
            request['timeout'] = self.settings.DEFAULT_TIMEOUT
        if request['headers'] is None:
            request['headers'] = self.settings.DEFAULT_HEADERS

        if request['meta'] is None:
            request['meta'] = {}
