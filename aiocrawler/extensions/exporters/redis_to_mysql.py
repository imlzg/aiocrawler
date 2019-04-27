# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin
# PROJECT   : aiocrawler
# File      : redis_to_mysql
import asyncio
import aioredis
import aiomysql
import traceback
import pickle
import json
from numpy import ceil
from aiocrawler.settings import BaseSettings
from aiocrawler.extensions.exporters.exporter import BaseExporter
from aiocrawler.item import Item
from typing import List, Iterable, Union


class RedisToMysql(BaseExporter):
    def __init__(self, settings: BaseSettings, item_class: Item, max_length: int = 128):

        BaseExporter.__init__(self, settings, item_class)

        self.__loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        self.__redis_pool: aioredis.ConnectionsPool = None
        self.__mysql_pool: aiomysql.Pool = None
        self.__redis_items_key = self.settings.REDIS_PROJECT_NAME + ':items'

        self.__max_length = max_length
        self.__table_name = item_class.__class__.__name__.lower()
        self.__fields = list(self.get_fields(item_class))

    async def __initialize__(self):
        """
        Initialize all necessary components.
        """

        if not self.settings.REDIS_URL or not self.settings.MYSQL_DB:
            raise ValueError('REDIS_URL or MYSQL_DB are not configured in {setting_name}'.format(
                setting_name=self.settings.__class__.__name__))
        else:
            self.logger.debug('Connecting to The Redis Server...')
            self.__redis_pool = await aioredis.create_pool(self.settings.REDIS_URL, loop=self.__loop)

            self.logger.debug('Connecting to The Mysql Server...')
            self.__mysql_pool: aiomysql.Pool = await aiomysql.create_pool(
                host=self.settings.MYSQL_HOST,
                user=self.settings.MYSQL_USER,
                password=self.settings.MYSQL_PASSWORD,
                db=self.settings.MYSQL_DB,
                loop=self.__loop
            )

            async with self.__mysql_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await self.__create_tables__(cur)

    async def __create_tables__(self, cur):
        await self.__create__(self.item_class, cur)

    async def __create__(self, item_class: Item, cur):
        self.logger.debug(f'Creating the table <name: {self.__table_name}>...')

        columns = ', '.join(map(lambda x: x + f' VARCHAR({self.__max_length})', self.get_fields(item_class)))
        sql = f'CREATE TABLE IF NOT EXISTS {self.__table_name} ' \
            f'({self.__table_name}_id INT NOT NULL AUTO_INCREMENT, {columns}, PRIMARY KEY({self.__table_name}_id));'
        await cur.execute(sql)

    async def __insert_into_mysql(self, item_values: Iterable, cur):

        column_str = ', '.join(self.__fields)

        values_str = ', '.join(['?' for _ in range(len(list(self.__fields)))])
        sql = f'INSERT INTO {self.__table_name} ({column_str}, VALUES ({values_str}));'
        await cur.executemany(sql, item_values)

    async def __get_redis_items(self, start: int, end: int):
        items = await self.__redis_pool.execute('lrange', self.__redis_items_key, start, end)
        count = len(items)
        self.logger.debug(f'Got {count} items <{start}, {end}> from '
                          f'The Redis Server <redis key: {self.__redis_items_key}>')
        return items

    async def main(self):
        total_count = await self.__redis_pool.execute('llen', self.__redis_items_key)
        self.logger.debug(f'Total {total_count} items in The Redis Server <redis key: {self.__redis_items_key}>')

        step = 1000
        batch = int(ceil(total_count / step))
        async with self.__mysql_pool.acquire() as conn:
            async with conn.cursor() as cur:
                for i in range(batch):
                    await self.__redis_to_mysql__(i*step, (i + 1)*step, cur)

    async def __redis_to_mysql__(self, start: int, end: int, cur):
        # sleep(0.05)
        items = await self.__get_redis_items(start, end)
        # items = filter(lambda x: x.__class__.__name__ == self.item_class.__class__.__name__, items)

        await self.__insert_into_mysql(self.__gen_item_data(items), cur)
        self.logger.success(f'The items <{start}, {end}> have been inserted into '
                            f'The Mysql Server <table_name: {self.__table_name}>')

    def __gen_item_data(self, items: Iterable[Item]) -> List:
        fields = self.get_fields(self.item_class)

        for item in items:
            try:
                item = pickle.loads(item)
            except:
                item = json.loads(item)
            data = []
            for column in fields:
                data.append(item.get(column, None))
            yield data

    def run(self):
        try:
            self.__loop.run_until_complete(self.__initialize__())
            self.__loop.run_until_complete(self.main())
        except Exception as e:
            self.logger.error(e)
            self.logger.error(traceback.format_exc(limit=10))
        finally:
            self.__loop.close()
