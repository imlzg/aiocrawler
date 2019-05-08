# coding: utf-8
from aiocrawler import Request
from aiocrawler import Response
from aiocrawler import BaseSettings
from typing import Union


class BaseMiddleware(object):
    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.logger = settings.LOGGER

    def process_request(self, request: Request):
        pass

    def process_response(self, request: Request, response: Response) -> Union[None, Request, Response]:
        pass

    def process_exception(self, request: Request, exception: Exception) -> Union[None, Request]:
        pass
