# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin1020
# PROJECT   : aiocrawler
from aioredis import ConnectionsPool
from aiocrawler import Item
from aiocrawler import Request
from aiocrawler import BaseSettings
from aiocrawler.extensions import Redis
from aiocrawler.filters.filter import BaseFilter


class RedisFilter(BaseFilter, Redis):
    def __init__(self, settings: BaseSettings, redis_pool: ConnectionsPool = None):
        BaseFilter.__init__(self, settings)
        Redis.__init__(self, settings, redis_pool)

        self.__redis_filters_key = settings.REDIS_PROJECT_NAME + ':filters'

    async def filter_request(self, request: Request):
        if request.dont_filter:
            return request

        elif await self.exist_request(request):
            return None
        return request

    async def filter_item(self, item: Item):
        sha1_item = self.sha1_item(item)
        resp = await self.redis_pool.execute('sismember', self.__redis_filters_key, sha1_item)
        if resp:
            self.logger.debug('The Item has existed in The Redis Server: {}'.format(sha1_item))
            return None
        else:
            await self.redis_pool.execute('sadd', self.__redis_filters_key, sha1_item)
            return item

    async def exist_request(self, request: Request):

        sha1_request = self.sha1_request(request)
        resp = await self.redis_pool.execute('sismember', self.__redis_filters_key, sha1_request)
        if resp:
            self.logger.debug('The Request has existed in The Redis Server: {}'.format(sha1_request))
            return True
        else:
            await self.redis_pool.execute('sadd', self.__redis_filters_key, sha1_request)
            return False
