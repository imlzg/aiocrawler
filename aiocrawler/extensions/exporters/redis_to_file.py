# coding: utf-8
# Date      : 2019/4/29
# Author    : kylin
# PROJECT   : aiocrawler
# File      : redis_to_file
import asyncio
import aiofiles
import traceback
from math import ceil
from pathlib import Path
from typing import Union
from json import dumps
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
        self.batch_size = batch_size
        self.__filename = Path(filename) if filename else Path('{}.json'.format(self.item_class_name.lower()))
        self.__file = None

    async def redis_to_json(self):
        total_count = await self.get_total_count()
        batches = int(ceil(total_count // self.batch_size))
        tasks = []

        for batch in range(batches):
            tasks.append(asyncio.ensure_future(
                self.__handle_items(batch * self.batch_size, (batch + 1) * self.batch_size)
            ))

        await asyncio.wait(tasks)

    async def __handle_items(self, start: int, end: int):
        items = await self.get_redis_items(start, end)
        items = map(lambda x: dumps(x), filter(lambda x: x.__class__.__name__ == self.item_class_name, items))
        data = ',\n'.join(items)
        await self.__file.write(data)

    async def main(self):
        self.__file = await aiofiles.open(self.__filename, 'w')
        await self.initialize_redis()
        if self.__filename.suffix == '.json':
            await self.redis_to_json()

        await self.__file.close()

    def run(self):
        try:
            self.loop.run_until_complete(self.main())
        except Exception as e:
            self.logger.error(traceback.format_exc(limit=10))
        finally:
            self.loop.close()
