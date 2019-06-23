# coding: utf-8
from typing import Set
from aiocrawler import Request
from aiocrawler import Item
from aiocrawler import BaseSettings
from aiocrawler.filters.filter import BaseFilter


class MemoryFilter(BaseFilter):
    def __init__(self, settings: BaseSettings):
        BaseFilter.__init__(self, settings)
        self.__sha1s: Set[str] = set()

    def filter_request(self, request: Request):
        sha1_request = self.sha1_request(request)
        if sha1_request not in self.__sha1s:
            self.__sha1s.add(sha1_request)
            return request

        self.logger.debug('The Request has existed in the Memory: {}'.format(sha1_request))
        return None

    def filter_item(self, item: Item):
        sha1_item = self.sha1_item(item)
        if sha1_item not in self.__sha1s:
            self.__sha1s.add(sha1_item)
            return item

        self.logger.debug('The Item has existed in the Memory: {}'.format(sha1_item))
        return None
