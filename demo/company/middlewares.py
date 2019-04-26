# coding: utf-8
# Date      : 2019-04-25
# PROJECT   : company
# File      : middlewares.py

from core.middlewares.middleware import BaseDownloaderMiddleware
from core.settings import BaseSettings


class CompanyMiddleware(BaseDownloaderMiddleware):
    def __init__(self, settings: BaseSettings):
        BaseDownloaderMiddleware.__init__(self, settings)

    def process_exception(self, request, response):
        request['dont_filter'] = True
        return request
