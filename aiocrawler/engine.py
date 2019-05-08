# coding: utf-8
import asyncio
import signal
import traceback
import aiojobs
from random import uniform
from time import sleep
from inspect import isfunction, iscoroutinefunction
from types import FunctionType
from typing import Iterator, List, Tuple, Union, Any, Dict

from aiocrawler import BaseSettings, Field, Item, Request, Response, Spider
from aiocrawler.downloaders import BaseDownloader
from aiocrawler.filters import BaseFilter
from aiocrawler.middlewares import (BaseMiddleware,
                                    SetDefaultRequestMiddleware,
                                    UserAgentMiddleware)
from aiocrawler.schedulers import BaseScheduler


class Engine(object):
    """
    The Engine schedules all components.
    """

    def __init__(self, spider: Spider,
                 settings: BaseSettings,
                 downloader_middlewares: List[Tuple[BaseMiddleware, int]] = None,
                 filters: BaseFilter = None,
                 scheduler: BaseScheduler = None,
                 downloader: BaseDownloader = None
                 ):

        self.spider = spider
        self.scheduler = scheduler
        self.settings = settings
        self.logger = settings.LOGGER

        self.filters = filters
        self.__middlewares = downloader_middlewares

        self.__downloader: BaseDownloader = downloader

        self.__crawled_count__ = 0
        self.__item_count__ = 0
        self.__log_interval__ = 30

        self.__signal_int_count = 0
        self.__is_close = False
        self.__closed_count = 0
        self.__shutdown_signal = False

        self.__pre_tasks: List[Tuple[FunctionType, Tuple[Any], Dict[str, Any]]] = []
        self.__completed_tasks: List[Tuple[FunctionType, Tuple[Any], Dict[str, Any]]] = []

    def add_pre_task(self, target, *args, **kwargs):
        self.__pre_tasks.append((target, args, kwargs))

    def add_completed_task(self, target, *args, **kwargs):
        self.__completed_tasks.append((target, args, kwargs))

    async def __run_task(self, target, *args, **kwargs):
        try:
            if iscoroutinefunction(target):
                return await target(*args, **kwargs)
            else:
                return target(*args, **kwargs)
        except Exception as e:
            self.logger.error(e)
            self.logger.error(traceback.format_exc(limit=10))

    async def __initialize(self):
        """
        Initialize all necessary components.
        """
        self.logger.debug('Initializing...')

        if not self.__downloader:
            from aiocrawler.downloaders.aio_downloader import AioDownloader
            self.__downloader = AioDownloader(self.settings)

        if not self.scheduler:
            if self.settings.REDIS_URL:
                from aiocrawler.schedulers import RedisScheduler
                self.scheduler = RedisScheduler(settings=self.settings)
                await self.scheduler.initialize_redis_pool()

                if not self.filters:
                    from aiocrawler.filters import RedisFilter
                    self.filters = RedisFilter(self.settings, redis_pool=self.scheduler.redis_pool)

                self.add_completed_task(self.scheduler.close_redis_pool)

            else:
                from aiocrawler.schedulers import MemoryScheduler
                self.scheduler = MemoryScheduler(self.settings, self.spider)

        if not self.filters:
            if self.settings.REDIS_URL:
                from aiocrawler.filters import RedisFilter
                self.filters = RedisFilter(self.settings, redis_pool=self.scheduler.redis_pool)
                await self.filters.initialize_redis_pool()
                self.add_completed_task(self.filters.close_redis_pool)

            else:
                from aiocrawler.filters import MemoryFilter
                self.filters = MemoryFilter(self.settings)

        if self.__middlewares is None:
            self.__middlewares = []

        default_middlewares = [
            (SetDefaultRequestMiddleware(self.settings), 1),
            (UserAgentMiddleware(self.settings), 2),
        ]
        self.__middlewares.extend(default_middlewares)
        self.__middlewares = sorted(
            self.__middlewares, key=lambda x: x[1])

        self.logger.debug('Initialized')

    async def __handle_response(self, request: Request, data: Union[Response, Exception, None]):
        """
        Handle the information returned by the downloader.
        :param request: Request
        :param data: Response or Exception
        """
        processed_data = None

        if isinstance(data, Exception):
            for downloader_middleware, _ in self.__middlewares:
                if iscoroutinefunction(downloader_middleware.process_exception):
                    processed_data = await downloader_middleware.process_exception(request, data)
                else:
                    processed_data = downloader_middleware.process_exception(
                        request, data)
                if processed_data:
                    break

            if processed_data is None:
                if isfunction(request.err_callback) and hasattr(self.spider.__class__, request.err_callback.__name__):
                    processed_data = request.err_callback(request, data)

        elif isinstance(data, Response):
            response = self.spider.__handle__(request, data)
            for downloader_middleware, _ in self.__middlewares:
                if iscoroutinefunction(downloader_middleware.process_response):
                    processed_data = await downloader_middleware.process_response(
                        request, response)
                else:
                    processed_data = downloader_middleware.process_response(
                        request, response)
                if processed_data:
                    if isinstance(processed_data, Response):
                        response = processed_data
                    break

            if isinstance(processed_data, Response) or processed_data is None:
                self.__crawled_count__ += 1
                self.logger.success('Crawled ({status}) <{method} {url}>',
                                    status=response.status,
                                    method=request.method,
                                    url=request.url
                                    )

                response.meta = request.meta
                if isfunction(request.callback) and hasattr(self.spider.__class__, request.callback.__name__):
                    processed_data = request.callback(response)

        if not processed_data:
            return

        if not isinstance(processed_data, Iterator) and not isinstance(processed_data, List):
            processed_data = [processed_data]

        tasks = []
        for one in processed_data:
            if isinstance(one, Request):
                if iscoroutinefunction(self.scheduler.send_request):
                    tasks.append(asyncio.ensure_future(self.scheduler.send_request(one)))
                else:
                    self.scheduler.send_request(one)
            elif isinstance(one, Item):
                self.__item_count__ += 1

                item_copy = one.__class__()
                for field in self.get_fields(one):
                    item_copy[field] = one.get(field, None)

                self.logger.success('Crawled from <{method} {url}> \n {item}',
                                    method=request.method, url=request.url, item=item_copy)
                tasks.append(asyncio.ensure_future(
                    self.__item_filter_and_send__(item_copy)))

        if len(tasks):
            await asyncio.wait(tasks)

    async def __item_filter_and_send__(self, item: Item):
        item = await self.__run_task(self.filters.filter_item, item)
        if item:
            await self.__run_task(self.scheduler.send_item, item)

    @staticmethod
    def get_fields(item: Item):
        for field_name in item.__class__.__dict__:
            if isinstance(getattr(item.__class__, field_name), Field):
                yield field_name

    async def __handle_word(self):
        """
        Handle the word from the scheduler.
        """
        try:
            while True:
                if self.__is_close:
                    self.__closed_count += 1
                    break

                await asyncio.sleep(self.settings.PROCESS_DALEY)
                word = await self.__run_task(self.scheduler.get_word)
                if word:
                    self.logger.debug(
                        'Making Request from word <word: {word}>'.format(word=word))
                    request = self.spider.make_request(word)
                    if request:
                        await self.__run_task(self.scheduler.send_request, request)
        except Exception as e:
            self.logger.error(e)
            self.logger.error(traceback.format_exc(limit=10))

    async def __handle_request(self):
        """
        Handle the request from scheduler.
        """
        try:
            while True:
                if self.__is_close:
                    self.__closed_count += 1
                    break

                await asyncio.sleep(self.settings.PROCESS_DALEY)
                request = await self.__run_task(self.scheduler.get_request)
                if request:
                    request = await self.__run_task(self.filters.filter_request, request)
                    if request:
                        for downloader_middleware, _ in self.__middlewares:
                            if iscoroutinefunction(downloader_middleware.process_request):
                                await downloader_middleware.process_request(request)
                            else:
                                downloader_middleware.process_request(request)

                        sleep(self.settings.DOWNLOAD_DALEY * uniform(0.5, 1.5))
                        data = await self.__downloader.get_response(request)
                        await self.__handle_response(request, data)

        except Exception as e:
            self.logger.error(e)
            self.logger.error(traceback.format_exc(limit=10))

    async def __log(self):
        """
        Log crawled information.
        """
        while True:
            request_count = await self.__run_task(self.scheduler.get_total_request)
            self.logger.debug('Total Crawled {crawled_count} Pages, {item_count} Items; '
                              'Total {request_count} Requests in The {scheduler_name}',
                              crawled_count=self.__crawled_count__,
                              item_count=self.__item_count__,
                              request_count=request_count,
                              scheduler_name=self.scheduler.__class__.__name__)
            await asyncio.sleep(self.__log_interval__)

    def __signal_int(self, signum, frame):
        self.__signal_int_count += 1
        self.logger.debug('Received SIGNAL INT, closing the Crawler...')
        self.close_crawler('SIGNAL INT Shutdown')
        if self.__signal_int_count >= 2:
            self.close_crawler('SIGNAL INT Shutdown by force', force=True)
            self.logger.debug('Received SIGNAL INT Over 2 times, closing the Crawler by force...')

    def close_crawler(self, message: str = "Normal shutdown", force: bool = False):
        self.logger.debug('Shutdown Reason: {message}', message=message)
        if force:
            self.__shutdown_signal = True
        else:
            self.__is_close = True

    async def __listening_closing_loop(self):
        count = self.settings.CONCURRENT_REQUESTS + self.settings.CONCURRENT_WORDS
        while True:
            if self.__closed_count >= count:
                self.__shutdown_signal = True
                break
            await asyncio.sleep(self.settings.PROCESS_DALEY)

    async def _main(self):

        for target, args, kwargs in self.__pre_tasks:
            await self.__run_task(target, *args, **kwargs)

        await self.__initialize()

        aiojobs_scheduler = await aiojobs.create_scheduler(limit=self.settings.AIOJOBS_LIMIT)
        for _ in range(self.settings.CONCURRENT_WORDS):
            await aiojobs_scheduler.spawn(self.__handle_word())

        for _ in range(self.settings.CONCURRENT_REQUESTS):
            await aiojobs_scheduler.spawn(self.__handle_request())

        await aiojobs_scheduler.spawn(self.__log())
        await aiojobs_scheduler.spawn(self.__listening_closing_loop())

        # Main event loop is listening the close signal
        while True:
            if self.__shutdown_signal:
                break
            await asyncio.sleep(0.1)

        await aiojobs_scheduler.close()

        for target, args, kwargs in self.__completed_tasks:
            await self.__run_task(target, *args, **kwargs)

    async def test(self):
        self.logger.error('test')

    def run(self):
        signal.signal(signal.SIGINT, self.__signal_int)

        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except:
            pass
        finally:
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(self._main())
            finally:
                for task in asyncio.Task.all_tasks(loop):
                    task.cancel()
                loop.stop()
                loop.run_forever()
                loop.close()
            self.logger.debug('The Crawler was closed')
