# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin1020
# PROJECT   : aiocrawler
# File      : redis_scheduler
import pickle
from time import time
from aiocrawler import Item
from aiocrawler import Request
from aiocrawler import BaseSettings
from aiocrawler.extensions import RedisConnector
from aioredis import ConnectionsPool
from aiocrawler.schedulers.scheduler import BaseScheduler


class RedisScheduler(BaseScheduler, RedisConnector):
    def __init__(self, settings: BaseSettings, redis_pool: ConnectionsPool = None):
        BaseScheduler.__init__(self, settings)
        RedisConnector.__init__(self, settings, redis_pool)

        self.__redis_words_key = self.settings.REDIS_PROJECT_NAME + ':words'
        self.__redis_requests_key = self.settings.REDIS_PROJECT_NAME + ':requests'
        self.__redis_items_key = self.settings.REDIS_PROJECT_NAME + ':items'

        self.__interval__ = 0.05
        self.__last_interaction = time()

    def _check(self):
        now = time()
        if now - self.__last_interaction <= self.__interval__:
            return True

        self.__last_interaction = now
        return False

    async def get_request(self):
        if self._check():
            return None

        request = await self.redis_pool.execute('lpop', self.__redis_requests_key)
        if request:
            request = pickle.loads(request)
        return request

    async def get_word(self):
        if self._check():
            return None

        key = await self.redis_pool.execute('lpop', self.__redis_words_key)
        if key:
            key = key.decode()
        return key

    async def send_request(self, request: Request):
        resp = await self.redis_pool.execute('lpush', self.__redis_requests_key,
                                             pickle.dumps(request))
        if resp == 0:
            self.logger.error('Send <Request> Failed <url: {url}> to redis server', url=request.url)

    async def send_item(self, item: Item):
        await self.redis_pool.execute('lpush', self.__redis_items_key, pickle.dumps(item))

    async def get_total_request(self):
        count = await self.redis_pool.execute('llen', self.__redis_requests_key)
        return count
