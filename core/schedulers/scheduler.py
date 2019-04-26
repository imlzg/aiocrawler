# coding: utf-8

from core.request import Request
from core.item import Item
from core.field import Field
from core.settings import BaseSettings


class BaseScheduler(object):
    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.logger = self.settings.LOGGER

    async def get_word(self):
        raise NotImplementedError('{} get_word not define'.format(self.__class__.__name__))

    async def get_request(self):
        raise NotImplementedError('{} get_request not define'.format(self.__class__.__name__))

    async def send_request(self, request: Request):
        raise NotImplementedError('{} send_request not define'.format(self.__class__.__name__))

    async def send_item(self, item: Item):
        raise NotImplementedError('{} send_item not define'.format(self.__class__.__name__))

    async def get_total_request(self):
        raise NotImplementedError('{} get_total_request not define'.format(self.__class__.__name__))
