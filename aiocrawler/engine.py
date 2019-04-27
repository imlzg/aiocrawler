# coding: utf-8
import traceback
import asyncio
import signal
from asyncio import AbstractEventLoop
from time import sleep
from aiocrawler.item import Item
from aiocrawler.field import Field
from aiocrawler.request import Request
from aiocrawler.filters.filter import BaseFilter
from aiocrawler.settings import BaseSettings
from aiocrawler.schedulers.scheduler import BaseScheduler
from typing import List, Union, Iterator, Tuple
from aiocrawler.middlewares.middleware import BaseDownloaderMiddleware
from aiocrawler.middlewares.user_agent_middleware import UserAgentMiddleware
from aiocrawler.middlewares.set_default_middleware import SetDefaultRequestMiddleware
from aiocrawler.middlewares.allowed_codes_middleware import AllowedCodesMiddleware
from aiocrawler.response import Response
from aiocrawler.spider import Spider
from aiocrawler.downloaders.downloader import BaseDownloader


class Engine(object):
    """
    The Engine schedules all components.
    """
    def __init__(self, spider: Spider,
                 settings: BaseSettings = None,
                 downloader_middlewares: List[Tuple[BaseDownloaderMiddleware, int]] = None,
                 filters: BaseFilter = None,
                 scheduler: BaseScheduler = None,
                 downloader: BaseDownloader = None
                 ):

        self.__spider = spider
        self.__scheduler = scheduler
        self.__settings = settings

        self.__filters = filters
        self.__downloader_middlewares = downloader_middlewares

        self.__downloader: BaseDownloader = downloader
        self.__logger = settings.LOGGER

        self.__crawled_count__ = 0
        self.__item_count__ = 0
        self.__log_interval__ = 30
        self.__loop: AbstractEventLoop = None

        self.__signal_int_count = 0
        self.__is_stop = False

    async def __process_run(self):
        """
        Initialize all necessary components.
        """
        if not self.__settings:
            self.__settings = BaseSettings()

        if not self.__downloader:
            from aiocrawler.downloaders.aio_downloader import AioDownloader
            self.__downloader = AioDownloader(self.__settings)

        if not self.__scheduler:
            from aiocrawler.schedulers.redis_scheduler import RedisScheduler
            self.__scheduler = RedisScheduler(settings=self.__settings)

        if not self.__filters:
            # Use Redis Filters by default.
            from aiocrawler.filters.redis_filter import RedisFilter
            self.__filters = RedisFilter(settings=self.__settings)

        if not self.__downloader_middlewares:
            self.__downloader_middlewares = []

        default_middlewares = [
            (SetDefaultRequestMiddleware(self.__settings), 1),
            (UserAgentMiddleware(self.__settings), 2),
            (AllowedCodesMiddleware(self.__settings), 3),
        ]
        self.__downloader_middlewares.extend(default_middlewares)
        self.__downloader_middlewares = sorted(self.__downloader_middlewares, key=lambda x: x[1])

        self.__is_process_run = True

    async def handle_response(self, request: Request, data: Union[Response, Exception, None]):
        """
        Handle the information returned by the downloader.
        :param request: Request
        :param data: Response or Exception
        """
        handled_data = None

        if isinstance(data, Exception):

            for downloader_middleware, _ in self.__downloader_middlewares:
                handled_data = downloader_middleware.process_exception(request, data)
                if handled_data:
                    break

            if handled_data is None:
                err_callback = getattr(self.__spider, request['err_callback'])
                handled_data = err_callback(request, data)

        elif isinstance(data, Response):
            response = self.__spider.__handle__(request, data)
            for downloader_middleware, _ in self.__downloader_middlewares:
                handled_data = downloader_middleware.process_response(request, response)
                if handled_data:
                    if isinstance(handled_data, Response):
                        response = handled_data
                    break

            if isinstance(handled_data, Response) or not handled_data:
                self.__crawled_count__ += 1
                self.__logger.success('Crawled ({status}) <{method} {url}>',
                                      status=response.status,
                                      method=request['method'],
                                      url=request['url']
                                      )

                response.meta = request['meta']
                callback = getattr(self.__spider, request['callback'])
                handled_data = callback(response)

        if not handled_data:
            return

        if not isinstance(handled_data, Iterator) and not isinstance(handled_data, List):
            handled_data = [handled_data]

        tasks = []
        for one in handled_data:
            if isinstance(one, Request):
                tasks.append(asyncio.ensure_future(self.__scheduler.send_request(one)))
            elif isinstance(one, Item):
                self.__item_count__ += 1

                item_copy = one.__class__()
                for field in self.get_fields(one):
                    item_copy[field] = one.get(field, None)

                self.__logger.success('Crawled from <{method} {url}> \n {item}',
                                      method=request['method'], url=request['url'], item=item_copy)
                tasks.append(asyncio.ensure_future(self.__item_filter_and_send__(item_copy)))

        if len(tasks):
            await asyncio.wait(tasks)

    async def __item_filter_and_send__(self, item: Item):
        item = await self.__filters.filter_item(item)
        if item:
            await self.__scheduler.send_item(item)

    @staticmethod
    def get_fields(item: Item):
        for field_name in item.__class__.__dict__:
            if isinstance(getattr(item.__class__, field_name), Field):
                yield field_name

    async def handle_word(self):
        """
        Handle the word from the scheduler.
        """
        try:
            while True:

                sleep(self.__settings.PROCESS_DALEY)
                word = await self.__scheduler.get_word()
                if word:
                    self.__logger.debug('Making Request from word <word: {word}>'.format(word=word))
                    request = self.__spider.make_request(word)
                    if request:
                        await self.__scheduler.send_request(request)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.__logger.error(e)
            self.__logger.error(traceback.format_exc(limit=10))

    async def handle_request(self):
        """
        Handle the request from scheduler.
        """
        try:
            while True:

                sleep(self.__settings.PROCESS_DALEY)
                request = await self.__scheduler.get_request()
                if request:
                    self.__logger.debug('Received 1 <Request> <url: {url}> from {scheduler_name}',
                                        url=request['url'],
                                        scheduler_name=self.__scheduler.__class__.__name__)
                    request = await self.__filters.filter_request(request)
                    if request:
                        for downloader_middleware, _ in self.__downloader_middlewares:
                            downloader_middleware.process_request(request)

                        sleep(self.__settings.DOWNLOAD_DALEY)
                        data = await self.__downloader.get_response(request)
                        await self.handle_response(request, data)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.__logger.error(e)
            self.__logger.error(traceback.format_exc(limit=10))

    async def __log__(self):
        """
        Log crawled information.
        """
        while True:

            request_count = await self.__scheduler.get_total_request()
            self.__logger.debug('Total Crawled {crawled_count} Pages, {item_count} Items; '
                                'Total {request_count} Requests in The {scheduler_name}',
                                crawled_count=self.__crawled_count__,
                                item_count=self.__item_count__,
                                request_count=request_count,
                                scheduler_name=self.__scheduler.__class__.__name__)
            await asyncio.sleep(self.__log_interval__)

    def signal_int(self, signum, frame):
        self.__signal_int_count += 1
        self.__logger.debug('Received SIGNAL INT {times} times.', times=self.__signal_int_count)
        if self.__signal_int_count >= 2:
            self.__logger.debug('Received SIGNAL INT over 2 times, closing the aiocrawler by force...')
            tasks = asyncio.Task.all_tasks()
            for task in tasks:
                task.cancel()
            asyncio.ensure_future(self.stop_loop())

    async def stop_loop(self):
        if self.__loop:
            self.__loop.stop()

    def run(self):
        """
        Start event loop.
        """
        signal.signal(signal.SIGINT, self.signal_int)

        self.__loop = asyncio.get_event_loop()
        try:
            self.__logger.debug('Initializing The Crawler...')
            self.__loop.run_until_complete(self.__process_run())

            for _ in range(self.__settings.CONCURRENT_WORDS):
                asyncio.ensure_future(self.handle_word())

            for _ in range(self.__settings.CONCURRENT_REQUESTS):
                asyncio.ensure_future(self.handle_request())

            asyncio.ensure_future(self.__log__())
            self.__logger.debug('The Crawler Initialized')

            self.__loop.run_forever()
        finally:
            self.__loop.close()
