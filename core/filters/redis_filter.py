# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin
# PROJECT   : aiocrawler
# File      : redis_filter
from re import findall
from hashlib import sha1
from yarl import URL
from core.item import Item
from core.filters.filter import BaseFilter
from core.settings import BaseSettings
from core.request import Request
from aioredis import create_pool, ConnectionsPool


class RedisFilter(BaseFilter):

    def __init__(self, settings: BaseSettings):
        BaseFilter.__init__(self, settings)

        self.__redis_pool: ConnectionsPool = None
        self.__redis_filters_key = settings.REDIS_PROJECT_NAME + ':filters'

    async def __initialize_redis_pool(self):
        if not self.settings.REDIS_URL:
            raise ValueError('REDIS_URL is not configured in {setting_name}'.format(
                setting_name=self.settings.__class__.__name__))
        else:
            self.__redis_pool = await create_pool(self.settings.REDIS_URL)

    async def filter_request(self, request: Request):
        if not self.__redis_pool:
            await self.__initialize_redis_pool()

        if request['dont_filter']:
            return request

        elif await self.exist_request(request):
            return None
        return request

    async def filter_item(self, item: Item):
        if not self.__redis_pool:
            await self.__initialize_redis_pool()

        hex_data = self.sha_item(item)
        resp = await self.__redis_pool.execute('sismember', self.__redis_filters_key, hex_data)
        if resp:
            self.logger.debug('The Item has existed in The Redis Server: {}'.format(hex_data))
            return item
        else:
            await self.__redis_pool.execute('sadd', self.__redis_filters_key, hex_data)
            return None

    async def exist_request(self, request: Request):

        hex_data = self.sha_request(request)
        resp = await self.__redis_pool.execute('sismember', self.__redis_filters_key, hex_data)
        if resp:
            self.logger.debug('The Request has existed in The Redis Server: {}'.format(hex_data))
            return True
        else:
            await self.__redis_pool.execute('sadd', self.__redis_filters_key, hex_data)
            return False

    @staticmethod
    def sha_item(item: Item):
        sha = sha1()
        for key, value in item.items():
            sha.update(str(key).encode())
            sha.update(str(value).encode())
        return sha.hexdigest()

    def sha_request(self, request: Request):
        sha = sha1()

        base_url, params = self.parse_url(request['url'])

        if request['method'] == 'GET':
            if request['params']:
                for data in request['params'].items():
                    params.append(data)

            params = sorted(params, key=lambda x: x)
        else:
            for key, value in sorted(request['params'].items(), key=lambda x: x[0]):
                sha.update(str(key).encode())
                sha.update(str(value).encode())

        for key, value in params:
            sha.update(str(key).encode())
            sha.update(str(value).encode())

        sha.update(request['method'].encode())
        sha.update(request['url'].encode())

        return sha.hexdigest()

    @staticmethod
    def parse_url(url: str):
        url = URL(url)

        base_url = str(url.parent) + url.path

        param_pattern = r'(\w+)=([^=&]*)'
        params = findall(param_pattern, url.query_string)
        return base_url, params
