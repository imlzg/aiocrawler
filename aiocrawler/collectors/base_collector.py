# coding: utf-8
from datetime import datetime
from aiocrawler import logger
from aiocrawler import Response, Request, Item


class BaseCollector(object):
    def __init__(self):
        self.spider_name: str = None
        self.running = False
        self.start_time: str = None

        self.done_startup_tasks = False
        self.done_cleanup_tasks = False

        self.word_received_count = 0

        self.request_count = 0
        self.request_method_count = {
            'GET': 0,
            'POST': 0
        }

        self.response_received_count = 0
        self.response_bytes = 0.0
        self.response_status_count = {
            '200': 0
        }

        self.exception_count = 0

        self.item_count: dict = {}

        self.finish_reason = 'Finished'
        self.finish_time: str = None

    @classmethod
    def get_collect_keys(cls):
        keys = [
            "spider_name",
            "running",
            "start_time",
            "done_startup_tasks",
            "done_cleanup_tasks",
            "word_received_count",
            "request_count",
            "request_method_count",
            "response_received_count",
            "response_bytes",
            "response_status_count",
            "exception_count",
            "item_count",
            "finish_reason",
            "finish_time"
        ]
        return keys

    def collect_word(self):
        self.word_received_count += 1

    def collect_request(self, request: Request):
        self.request_count += 1
        self.request_method_count[request.method] = self.request_method_count[request.method] + 1 \
            if request.method in self.request_method_count.keys() else 1

    def collect_item(self, item: Item):
        classname = item.__class__.__name__
        self.item_count = self.item_count[classname] + 1 if classname in self.item_count.keys() else 1

    def collect_response_received(self, response: Response):
        self.response_received_count += 1
        self.response_bytes += len(response.text)

        status = str(response.status)
        self.response_status_count[status] = self.response_status_count[status] + 1\
            if status in self.response_status_count.keys() else 1

    def collect_downloader_exception(self):
        self.exception_count += 1

    def collect_start(self, spider_name: str, formatter: str = '%Y-%m-%d %H:%M:%S'):
        self.done_startup_tasks = True
        self.spider_name = spider_name
        self.start_time = datetime.now().strftime(formatter)
        self.running = True

    def collect_finish(self, formatter: str = '%Y-%m-%d %H:%M:%S'):
        self.done_cleanup_tasks = True
        self.running = False
        self.finish_time = datetime.now().strftime(formatter)

    def output_stats(self):
        logger.debug('Dumping Aiocrawler stats:')
        for key in self.get_collect_keys():
            print('{classname}: "{key}": {value}'.format(
                classname=self.__class__.__name__, key=key, value=getattr(self, key)))
