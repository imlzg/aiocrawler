# coding: utf-8
from ujson import dumps
from aiocrawler import logger
from aiocrawler import Response, Request, Item
from aiocrawler.collectors import BaseCollector


class ClientCollector(BaseCollector):
    def __init__(self, ws, uuid: str):
        BaseCollector.__init__(self)
        self._ws = ws
        self._uuid = uuid

    async def send_json(self, info):
        if self._ws.closed:
            logger.error('The websocket connection is closed')
            return

        data = {
            'uuid': self._uuid,
            'from': self.__class__.__name__,
            'info': info
        }
        await self._ws.send_str(dumps(data))

    async def collect_start(self, spider_name: str, formatter: str = '%Y-%m-%d %H:%M:%S'):
        BaseCollector.collect_start(self, spider_name, formatter)
        await self.send_json({
                'spider_name': self.spider_name,
                'start_time': self.start_time,
                'running': self.running,
                'done_startup_tasks': self.done_startup_tasks
            })

    async def collect_word(self):
        BaseCollector.collect_word(self)
        await self.send_json({
            'word_received_count': self.word_received_count
        })

    async def collect_request(self, request: Request):
        BaseCollector.collect_request(self, request)
        await self.send_json({
            'request_count': self.request_count,
            'request_method_count': self.request_method_count
        })

    async def collect_response_received(self, response: Response):
        BaseCollector.collect_response_received(self, response)
        await self.send_json({
            'response_received_count': self.response_received_count,
            'response_bytes': self.response_bytes,
            'response_status_count': self.response_status_count
        })

    async def collect_downloader_exception(self):
        BaseCollector.collect_downloader_exception(self)
        await self.send_json({
            'exception_count': self.exception_count
        })

    async def collect_item(self, item: Item):
        BaseCollector.collect_item(self, item)
        await self.send_json({
            'item_count': self.item_count
        })

    async def collect_finish(self, formatter: str = '%Y-%m-%d %H:%M:%S'):
        BaseCollector.collect_finish(self, formatter)
        await self.send_json({
            'done_cleanup_tasks': self.done_cleanup_tasks,
            'running': self.running,
            'finish_time': self.finish_time,
            'finish_reason': self.finish_reason
        })
