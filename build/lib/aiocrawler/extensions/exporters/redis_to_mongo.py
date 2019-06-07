# coding: utf-8
# Date      : 2019/5/2
# Author    : kylin
# PROJECT   : aiocrawler
# File      : redis_to_mongo
import os
import asyncio
import traceback
from math import ceil
from aiocrawler import Item
from aiocrawler import BaseSettings
from motor.motor_asyncio import AsyncIOMotorClient
from aiocrawler.extensions.exporters.redis_exporter import RedisExporter


class RedisToMongo(RedisExporter):
    def __init__(self, settings: BaseSettings,
                 item_class: Item,
                 loop: asyncio.AbstractEventLoop = None,
                 table_name: str = None,
                 batch_size: int = 1000):
        RedisExporter.__init__(self, settings, item_class, loop=loop)
        self.batch_size = batch_size

        self.client = None
        self.table_name = table_name if table_name else self.item_class_name.lower()
        self.db = None
        self.mongo_session = None
        self.table = None

    async def initialize_mongo(self):
        mongo_host = self.settings.MONGO_HOST or os.environ.login_get('MONGO_HOST', None)

        if mongo_host is None:
            raise ValueError('MONGO_HOST is not configured in {setting_name} or the Environmental variables'.format(
                setting_name=self.settings.__class__.__name__))

        mongo_port = self.settings.MONGO_PORT or os.environ.login_get('MONGO_PORT', 27017)
        mongo_user = self.settings.MONGO_USER or os.environ.login_get('MONGO_USER', None)
        mongo_password = self.settings.MONGO_PASSWORD or os.environ.login_get('MONGO_PASSWORD', None)

        self.client = AsyncIOMotorClient(host=mongo_host,
                                         port=mongo_port,
                                         username=mongo_user,
                                         password=mongo_password)

        db_name = self.settings.MONGO_DB or os.environ.login_get('MONGO_DB', None) or self.settings.PROJECT_NAME
        self.db = self.client[db_name]
        self.table = self.db[self.table_name]
        self.mongo_session = await self.client.start_session()

    async def redis_to_mongo(self):
        tasks = [
            asyncio.ensure_future(self.initialize_redis()),
            asyncio.ensure_future(self.initialize_mongo())
        ]
        await asyncio.wait(tasks)

        total_count = await self.get_total_count()
        batches = int(ceil(total_count / self.batch_size))
        tasks = [
            asyncio.ensure_future(self.__save_to_mongo(batch * self.batch_size, (batch + 1) * self.batch_size))
            for batch in range(batches)
        ]
        if len(tasks):
            await asyncio.wait(tasks)

        await self.mongo_session.end_session()
        self.redis_pool.close()
        await self.redis_pool.wait_closed()

    async def __save_to_mongo(self, start: int, end: int):
        items = await self.get_redis_items(start, end)
        items = filter(lambda x: x.__class__.__name__ == self.item_class_name, items)
        await self.table.insert_many(items, session=self.mongo_session)

    def run(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.redis_to_mongo())
            self.logger.success('The {item_name} have been inserted into the Mongo Server. ',
                                item_name=self.item_class_name)
        except:
            self.logger.error(traceback.format_exc())
        finally:
            loop.close()
