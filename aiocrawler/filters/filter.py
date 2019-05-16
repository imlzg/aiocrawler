# coding: utf-8
from yarl import URL
from re import findall
from hashlib import sha1
from typing import Union
from aiocrawler import Item
from aiocrawler import Request
from aiocrawler import BaseSettings, logger


class BaseFilter(object):
    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.logger = logger

    async def filter_request(self, request: Request) -> Union[None, Request]:
        raise NotImplementedError('{} filter_request is not define'.format(self.__class__.__name__))

    async def filter_item(self, item: Item):
        raise NotImplementedError('{} filter_item is not define'.format(self.__class__.__name__))

    @staticmethod
    def sha1_item(item: Item):
        sha = sha1()
        for key, value in item.items():
            sha.update(str(key).encode())
            sha.update(str(value).encode())
        return sha.hexdigest()

    def sha1_request(self, request: Request):
        sha = sha1()

        base_url, params = self.parse_url(request.url)

        if request.method == 'GET':
            if request.params:
                for data in request.params.items():
                    params.append(data)

            params = sorted(params, key=lambda x: x)
        else:
            for key, value in sorted(request.params.items(), key=lambda x: x[0]):
                sha.update(str(key).encode())
                sha.update(str(value).encode())

        for key, value in params:
            sha.update(str(key).encode())
            sha.update(str(value).encode())

        sha.update(request.method.encode())
        sha.update(request.url.encode())

        return sha.hexdigest()

    @staticmethod
    def parse_url(url: str):
        url = URL(url)

        base_url = str(url.parent) + url.path

        param_pattern = r'(\w+)=([^=&]*)'
        params = findall(param_pattern, url.query_string)
        return base_url, params
