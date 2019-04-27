# coding: utf-8
# Date      : 2019/4/27
# Author    : kylin1020
# PROJECT   : aiocrawler
# File      : local_scheduler
from aiocrawler import BaseScheduler
from aiocrawler import BaseSettings
from aiocrawler import Item
from aiocrawler import Request


class LocalScheduler(BaseScheduler):
    def __init__(self, settings: BaseSettings):
        BaseScheduler.__init__(self, settings)

    def get_total_request(self):
        pass

    def get_request(self):
        pass

    def get_word(self):
        pass

    def send_item(self, item: Item):
        pass

    def send_request(self, request: Request):
        pass
