# coding: utf-8
from aiocrawler import Item
from aiocrawler import Request
from aiocrawler import BaseSettings, logger


class BaseScheduler(object):
    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.logger = logger

    def get_word(self):
        raise NotImplementedError('{} get_word not define'.format(self.__class__.__name__))

    def get_request(self):
        raise NotImplementedError('{} get_request not define'.format(self.__class__.__name__))

    def send_request(self, request: Request):
        raise NotImplementedError('{} send_request not define'.format(self.__class__.__name__))

    def send_item(self, item: Item):
        raise NotImplementedError('{} send_item not define'.format(self.__class__.__name__))

    def get_total_request(self):
        raise NotImplementedError('{} get_total_request not define'.format(self.__class__.__name__))
