# coding: utf-8
from aiocrawler.request import Request
from typing import Union
from aiocrawler.settings import BaseSettings
from aiocrawler.item import Item


class BaseFilter(object):
    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.logger = settings.LOGGER

    async def filter_request(self, request: Request) -> Union[None, Request]:
        raise NotImplementedError('{} filter_request is not define'.format(self.__class__.__name__))

    async def filter_item(self, item: Item):
        raise NotImplementedError('{} filter_item is not define'.format(self.__class__.__name__))
