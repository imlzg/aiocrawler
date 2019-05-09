# coding: utf-8
# Date      : 2019/4/29
# Author    : kylin
# PROJECT   : aiocrawler
# File      : redis_to_mongodb
import asyncio
import aiofiles
import traceback
from math import ceil
from pathlib import Path
from typing import Union, Iterable
from aiocrawler.extensions.exporters.redis_exporter import RedisExporter
from aiocrawler import BaseSettings
from aiocrawler import Item


class RedisToFile(RedisExporter):
    def __init__(self, settings: BaseSettings,
                 item_class: Item,
                 loop: asyncio.AbstractEventLoop = None,
                 batch_size: int = 1000,
                 filename: Union[Path, str] = None):

        RedisExporter.__init__(self, settings, item_class, loop)
        self.__filename = Path(filename) if filename else Path('{}.csv'.format(
            vars(self.item_class).get('item_name', self.item_class_name.lower())))

        self.batch_size = batch_size
        self.__file = None
        self.__fields = list(self.get_fields(item_class))

    async def redis_to_csv(self):
        total_count = await self.get_total_count()
        batches = int(ceil(total_count / self.batch_size))
        tasks = [
            asyncio.ensure_future(self.__save(batch * self.batch_size, (batch + 1) * self.batch_size))
            for batch in range(batches)
        ]
        if len(tasks):
            headers = ','.join(self.__fields) + '\n'
            await self.__file.write(headers)

            await asyncio.wait(tasks)

    async def __save(self, start: int, end: int):
        items = await self.get_redis_items(start, end)
        items = filter(lambda x: x.__class__.__name__ == self.item_class_name, items)
        data = '\n'.join(self.__format_items(items))
        await self.__file.write(data)

    def __format_items(self, items: Iterable[Item]):
        for item in items:
            data = ','.join(['"{}"'.format(item.get(field), '') for field in self.__fields])
            yield data

    async def main(self):
        self.__file = await aiofiles.open(self.__filename, 'w')
        await self.initialize_redis()
        await self.redis_to_csv()
        await self.__file.shutdown_task()
        self.redis_pool.close()
        await self.redis_pool.wait_closed()

    def run(self):
        if self.__filename.is_file():
            self.logger.error('The {filename} has exists in {dir}',
                              filename=self.__filename.name, dir=self.__filename.absolute().parent)
            return

        if self.loop is None:
            self.loop = asyncio.get_event_loop()
        try:
            self.loop.run_until_complete(self.main())
        except Exception as e:
            self.logger.error(traceback.format_exc(limit=10))
        finally:
            self.loop.close()
