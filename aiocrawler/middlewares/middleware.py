# coding: utf-8
from aiocrawler import Request
from aiocrawler import Response
from aiocrawler import Item
from aiocrawler import BaseSettings
from aiocrawler.engine import Engine
from typing import Union


class BaseMiddleware(object):
    def __init__(self, settings: BaseSettings, engine: Engine):
        self.settings = settings
        self.logger = settings.LOGGER
        self.engine = engine

    def process_request(self, request: Request):
        pass

    def process_response(self, request: Request, response: Response) -> Union[None, Request, Response]:
        pass

    def process_exception(self, request: Request, exception: Exception) -> Union[None, Request]:
        pass

    def process_item(self, item: Item) -> Union[None, Item]:
        pass
