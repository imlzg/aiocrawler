# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin1020
# PROJECT   : aiocrawler
# File      : redis_scheduler
import pickle
from aiocrawler import Item
from aiocrawler import Request
from aiocrawler import BaseSettings
from aioredis import create_pool, ConnectionsPool
from aiocrawler.schedulers.scheduler import BaseScheduler


class RedisScheduler(BaseScheduler):
    def __init__(self, settings: BaseSettings):
        BaseScheduler.__init__(self, settings)

        self.redis_pool: ConnectionsPool = None
        self.__redis_words_key = self.settings.REDIS_PROJECT_NAME + ':words'
        self.__redis_requests_key = self.settings.REDIS_PROJECT_NAME + ':requests'
        self.__redis_items_key = self.settings.REDIS_PROJECT_NAME + ':items'

    async def initialize_redis_pool(self):
        if not self.settings.REDIS_URL:
            raise ValueError('REDIS_URL are not configured in {setting_name}'.format(
                setting_name=self.settings.__class__.__name__))
        else:
            self.redis_pool = await create_pool(self.settings.REDIS_URL)

    async def get_request(self):
        request = await self.redis_pool.execute('lpop', self.__redis_requests_key)
        if request:
            request = pickle.loads(request)
        return request

    async def get_word(self):
        key = await self.redis_pool.execute('lpop', self.__redis_words_key)
        if key:
            key = key.decode()
        return key

    async def send_request(self, request: Request):
        resp = await self.redis_pool.execute('lpush', self.__redis_requests_key,
                                             pickle.dumps(request))
        if resp == 0:
            self.logger.error('Send <Request> Failed <url: {url}> to redis server', url=request['url'])

    async def send_item(self, item: Item):
        await self.redis_pool.execute('lpush', self.__redis_items_key, pickle.dumps(item))

    async def get_total_request(self):
        count = await self.redis_pool.execute('llen', self.__redis_requests_key)
        return count
