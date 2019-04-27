# coding: utf-8
from aiocrawler.request import Request
from aiocrawler.settings import BaseSettings
from aiocrawler.response import Response
from typing import Union


class BaseDownloaderMiddleware(object):
    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.logger = self.settings.LOGGER

    def process_request(self, request: Request):
        pass

    def process_response(self, request: Request, response: Response) -> Union[None, Request, Response]:
        pass

    def process_exception(self, request: Request, exception: Exception) -> Union[None, Request]:
        pass
