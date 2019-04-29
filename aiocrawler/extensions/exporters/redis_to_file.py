# coding: utf-8
# Date      : 2019/4/29
# Author    : kylin
# PROJECT   : aiocrawler
# File      : redis_to_file
import asyncio
import aiofiles
import traceback
from math import ceil
from aiocrawler.extensions.exporters.redis_exporter import RedisExporter
from aiocrawler import BaseSettings
from aiocrawler import Item


class RedisToFile(RedisExporter):
    def __init__(self, settings: BaseSettings,
                 item_class: Item,
                 loop: asyncio.AbstractEventLoop,
                 step: int = 1000,
                 output_type: str = 'json'):
        RedisExporter.__init__(self, settings, item_class, loop)
        self.step = step
        self.output_type = output_type
        self.filename = self.__get_filename()
        self.__file = None

    def __get_filename(self):
        if self.output_type == 'text':
            filename = self.item_class_name.lower() + '.txt'
        else:
            filename = self.item_class_name.lower() + '.json'
        return filename

    async def redis_to_json(self):
        total_count = await self.get_total_count()
        batch_size = int(ceil(total_count // self.step))
        tasks = []

        for batch in range(batch_size):
            tasks.append(asyncio.ensure_future(self.__handle_items(batch * self.step, (batch + 1) * self.step)))

        await asyncio.wait(tasks)

    async def __handle_items(self, start: int, end: int):
        items = await self.get_redis_items(start, end)
        tasks = []
        for item in items:
            tasks.append(asyncio.ensure_future(self.__save_to_json(item)))

        await asyncio.wait(tasks)

    async def __save_to_json(self, item: Item):
        pass

    async def main(self):
        self.__file = await aiofiles.open(self.filename, 'w')
        await self.initialize_redis()
        if self.output_type == 'json':
            await self.redis_to_json()

    def run(self):
        try:
            self.loop.run_until_complete(self.main())
        except Exception as e:
            self.logger.error(traceback.format_exc(limit=10))
        finally:
            self.loop.close()
