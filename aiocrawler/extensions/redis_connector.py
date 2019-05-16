# coding: utf-8
import os
from aiocrawler import BaseSettings, logger
from aioredis import create_pool, ConnectionsPool


class RedisConnector(object):
    def __init__(self, settings: BaseSettings, redis_pool: ConnectionsPool = None):
        self.logger = logger
        self.settings = settings
        self.redis_pool: ConnectionsPool = redis_pool

    async def create_redis_pool(self, redis_url: str = None):
        if self.redis_pool:
            return

        redis_url = redis_url or self.settings.REDIS_URL or os.environ.login_get('REDIS_URL', None)
        if not redis_url:
            raise ValueError('REDIS_URL are not configured in {setting_name} or the Environmental variables'.format(
                setting_name=self.settings.__class__.__name__))
        else:
            self.logger.debug('Connecting to the Redis Server...')
            self.redis_pool = await create_pool(self.settings.REDIS_URL)
            self.logger.success('Connected to the Redis Server')

    async def close_redis_pool(self):
        if self.redis_pool:
            self.redis_pool.close()
            await self.redis_pool.wait_closed()
            self.logger.debug('The Redis Pool is closed')
