# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin1020
# PROJECT   : aiocrawler
# File      : redis_filter
import os
from aiocrawler import Item
from aiocrawler import Request
from aiocrawler import BaseSettings
from aiocrawler.filters.filter import BaseFilter
from aioredis import create_pool, ConnectionsPool


class RedisFilter(BaseFilter):

    def __init__(self, settings: BaseSettings, redis_pool: ConnectionsPool = None):
        BaseFilter.__init__(self, settings)

        self.__redis_pool: ConnectionsPool = redis_pool
        self.__redis_filters_key = settings.REDIS_PROJECT_NAME + ':filters'

    async def initialize_redis_pool(self):
        redis_url = self.settings.REDIS_URL or os.environ.get('REDIS_URL', None)
        if not redis_url:
            raise ValueError('REDIS_URL is not configured in {setting_name} or the Environmental variables'.format(
                setting_name=self.settings.__class__.__name__))
        else:
            self.__redis_pool = await create_pool(self.settings.REDIS_URL)

    async def filter_request(self, request: Request):
        if request.dont_filter:
            return request

        elif await self.exist_request(request):
            return None
        return request

    async def filter_item(self, item: Item):
        sha1_item = self.sha1_item(item)
        resp = await self.__redis_pool.execute('sismember', self.__redis_filters_key, sha1_item)
        if resp:
            self.logger.debug('The Item has existed in The Redis Server: {}'.format(sha1_item))
            return None
        else:
            await self.__redis_pool.execute('sadd', self.__redis_filters_key, sha1_item)
            return item

    async def exist_request(self, request: Request):

        sha1_request = self.sha1_request(request)
        resp = await self.__redis_pool.execute('sismember', self.__redis_filters_key, sha1_request)
        if resp:
            self.logger.debug('The Request has existed in The Redis Server: {}'.format(sha1_request))
            return True
        else:
            await self.__redis_pool.execute('sadd', self.__redis_filters_key, sha1_request)
            return False
