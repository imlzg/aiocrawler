# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin
# PROJECT   : aiocrawler
# File      : redis_filter
from re import findall
from hashlib import sha1
from yarl import URL
from core.filters.filter import BaseFilter
from core.settings import BaseSettings
from core.request import Request


class RedisFilter(BaseFilter):

    def __init__(self, settings: BaseSettings):
        BaseFilter.__init__(self, settings)

        self.__redis_pool = None
        self.__redis_filters_key = settings.REDIS_PROJECT_NAME + ':filters'

    async def __initialize_redis_pool(self):
        if not self.settings.REDIS_URL:
            raise ValueError('REDIS_URL is not configured in {setting_name}'.format(
                setting_name=self.settings.__class__.__name__))
        else:
            from aioredis import create_pool
            self.__redis_pool = await create_pool(self.settings.REDIS_URL)

    async def filter_request(self, request: Request):
        if not self.__redis_pool:
            await self.__initialize_redis_pool()

        if request['dont_filter']:
            return request

        elif await self.exist_request(request):
            return None
        return request

    async def exist_request(self, request: Request):

        hex_data = self.sha_request(request)
        resp = await self.__redis_pool.execute('sismember', self.__redis_filters_key, hex_data)
        if resp:
            self.logger.debug('The Request has existed in redis server: {}'.format(hex_data))
            return True
        else:
            await self.__redis_pool.execute('sadd', self.__redis_filters_key, hex_data)
            return False

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

        hex_data = sha.hexdigest()
        return hex_data

    @staticmethod
    def parse_url(url: str):
        url = URL(url)

        base_url = str(url.parent) + url.path

        param_pattern = r'(\w+)=([^=&]*)'
        params = findall(param_pattern, url.query_string)
        return base_url, params
