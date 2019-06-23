# coding: utf-8
from aiocrawler import BaseSettings
from aiocrawler.spider import Spider
from aiocrawler import Request
from aiocrawler import Item
from typing import List
from pickle import dumps, loads
from aiocrawler.schedulers.scheduler import BaseScheduler


class MemoryScheduler(BaseScheduler):
    def __init__(self, settings: BaseSettings, spider: Spider):
        BaseScheduler.__init__(self, settings)
        self.__spider = spider
        self.__requests: List[Request] = []
        self.__items: List[Item] = []
        self.__error_requests = set()
        self.__spider.words = [] if self.__spider.words is None else self.__spider.words

    def get_word(self):
        if len(self.__spider.words):
            return self.__spider.words.pop(0)
        return None

    def get_request(self):
        if len(self.__requests):
            return self.__requests.pop(0)
        return None

    def send_request(self, request: Request):
        self.__requests.append(request)

    def send_item(self, item: Item):
        self.__items.append(item)

    def get_total_request(self):
        return len(self.__requests)

    def append_error_request(self, request: Request):
        self.__error_requests.add(dumps(request))
