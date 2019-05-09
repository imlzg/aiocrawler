# coding: utf-8
import asyncio
import signal
import traceback
from random import uniform
from time import sleep
from inspect import isfunction, iscoroutinefunction
from typing import Iterator, List, Tuple, Union, Any, Dict, Callable

from aiocrawler import BaseSettings, Field, Item, Request, Response, Spider
from aiocrawler.downloaders import BaseDownloader
from aiocrawler.filters import BaseFilter
from aiocrawler.schedulers import BaseScheduler
from aiocrawler.job_scheduler import JobScheduler


class Engine(object):
    """
    The Engine schedules all components.
    """

    def __init__(self, spider: Spider,
                 settings: BaseSettings,
                 filters: BaseFilter = None,
                 scheduler: BaseScheduler = None,
                 downloader: BaseDownloader = None
                 ):

        self._spider = spider
        self._scheduler = scheduler
        self._settings = settings
        self._logger = settings.LOGGER

        self._filters = filters
        self.__middlewares = []

        self.__downloader: BaseDownloader = downloader

        self.__crawled_count__ = 0
        self.__item_count__ = 0
        self.__log_interval__ = 30

        self.__signal_int_count = 0

        self.__pre_tasks: List[Tuple[Callable, Tuple[Any], Dict[str, Any]]] = []
        self.__pre_task_done = False
        self.__completed_tasks: List[Tuple[Callable, Tuple[Any], Dict[str, Any]]] = []

        self.__job_scheduler = JobScheduler(settings=self._settings)
        self.__closed_reason = 'Finished'

    def add_pre_task(self, target, *args, **kwargs):
        # prevent adding new target after pre tasks has been done
        if self.__pre_task_done:
            self._logger.warning('pre_tasks has been done')
            return
        if callable(target):
            self.__pre_tasks.append((target, args, kwargs))

    def add_completed_task(self, target, *args, **kwargs):
        if callable(target):
            self.__completed_tasks.append((target, args, kwargs))

    async def __run_task(self, target, *args, **kwargs):
        try:
            if iscoroutinefunction(target):
                return await target(*args, **kwargs)
            else:
                return target(*args, **kwargs)
        except Exception as _:
            self._logger.error(traceback.format_exc())

    async def __initialize(self):
        """
        Initialize all necessary components.
        """
        self._logger.debug('Initializing...')

        if not self.__downloader:
            from aiocrawler.downloaders.aio_downloader import AioDownloader
            self.__downloader = AioDownloader(self._settings)

        if not self._scheduler:
            if self._settings.REDIS_URL:
                from aiocrawler.schedulers import RedisScheduler
                self._scheduler = RedisScheduler(settings=self._settings)
                await self._scheduler.initialize_redis_pool()

                if not self._filters:
                    from aiocrawler.filters import RedisFilter
                    self._filters = RedisFilter(self._settings, redis_pool=self._scheduler.redis_pool)

                self.add_completed_task(self._scheduler.close_redis_pool)

            else:
                from aiocrawler.schedulers import MemoryScheduler
                self._scheduler = MemoryScheduler(self._settings, self._spider)

        if not self._filters:
            if self._settings.REDIS_URL:
                from aiocrawler.filters import RedisFilter
                self._filters = RedisFilter(self._settings, redis_pool=self._scheduler.redis_pool)
                await self._filters.initialize_redis_pool()
                self.add_completed_task(self._filters.close_redis_pool)

            else:
                from aiocrawler.filters import MemoryFilter
                self._filters = MemoryFilter(self._settings)

        from aiocrawler.middlewares import BaseMiddleware, SetDefaultRequestMiddleware, UserAgentMiddleware

        default_middlewares = [
            (SetDefaultRequestMiddleware, 1),
            (UserAgentMiddleware, 2),
        ]
        self.__middlewares.extend(default_middlewares)
        self.__middlewares.extend(self._settings.MIDDLEWARES)

        self.__middlewares = sorted(self.__middlewares, key=lambda x: x[1])

        self.__middlewares = list(map(lambda x: x[0](self._settings, self), self.__middlewares))

        self._logger.debug('Initialized')

    async def __handle_response(self, request: Request, data: Union[Response, Exception, None]):
        """
        Handle the information returned by the downloader.
        :param request: Request
        :param data: Response or Exception
        """
        processed_data = None

        if isinstance(data, Exception):
            for middleware in self.__middlewares:
                processed_data = await self.__run_task(middleware.process_exception, request, data)
                if processed_data:
                    break

            if processed_data is None:
                if isfunction(request.err_callback) and hasattr(self._spider.__class__, request.err_callback.__name__):
                    processed_data = request.err_callback(request, data)

        elif isinstance(data, Response):
            response = self._spider.__handle__(request, data)
            for middleware in self.__middlewares:
                if iscoroutinefunction(middleware.process_response):
                    processed_data = await middleware.process_response(
                        request, response)
                else:
                    processed_data = middleware.process_response(
                        request, response)
                if processed_data:
                    if isinstance(processed_data, Response):
                        response = processed_data
                    break

            if isinstance(processed_data, Response) or processed_data is None:
                self.__crawled_count__ += 1
                self._logger.success('Crawled ({status}) <{method} {url}>',
                                     status=response.status,
                                     method=request.method,
                                     url=request.url
                                     )

                response.meta = request.meta
                if isfunction(request.callback) and hasattr(self._spider.__class__, request.callback.__name__):
                    processed_data = request.callback(response)

        if not processed_data:
            return

        if not isinstance(processed_data, Iterator) and not isinstance(processed_data, List):
            processed_data = [processed_data]

        tasks = []
        for one in processed_data:
            if isinstance(one, Request):
                if iscoroutinefunction(self._scheduler.send_request):
                    tasks.append(asyncio.ensure_future(self._scheduler.send_request(one)))
                else:
                    self._scheduler.send_request(one)
            elif isinstance(one, Item):
                self.__item_count__ += 1

                item_copy = one.__class__()
                for field in self.get_fields(one):
                    item_copy[field] = one.get(field, None)

                self._logger.success('Crawled from <{method} {url}> \n {item}',
                                     method=request.method, url=request.url, item=item_copy)
                tasks.append(asyncio.ensure_future(
                    self.__item_filter_and_send__(item_copy)))

        if len(tasks):
            await asyncio.wait(tasks)

    async def __item_filter_and_send__(self, item: Item):
        item = await self.__run_task(self._filters.filter_item, item)
        if item:
            await self.__run_task(self._scheduler.send_item, item)

    @staticmethod
    def get_fields(item: Item):
        for field_name in item.__class__.__dict__:
            if isinstance(getattr(item.__class__, field_name), Field):
                yield field_name

    async def __handle_word(self):
        """
        Handle the word from the scheduler.
        """
        word = await self.__run_task(self._scheduler.get_word)
        if word:
            self._logger.debug(
                'Making Request from word <word: {word}>'.format(word=word))
            request = self._spider.make_request(word)
            if request:
                await self.__run_task(self._scheduler.send_request, request)

    async def __handle_request(self):
        """
        Handle the request from scheduler.
        """
        request = await self.__run_task(self._scheduler.get_request)
        if request:
            request = await self.__run_task(self._filters.filter_request, request)
            if request:
                for downloader_middleware in self.__middlewares:
                    if iscoroutinefunction(downloader_middleware.process_request):
                        await downloader_middleware.process_request(request)
                    else:
                        downloader_middleware.process_request(request)

                sleep(self._settings.DOWNLOAD_DALEY * uniform(0.5, 1.5))
                data = await self.__downloader.get_response(request)
                await self.__handle_response(request, data)

    # async def __log(self):
    #     """
    #     Log crawled information.
    #     """
    #     while True:
    #         if self.__job_scheduler.closing:
    #             break
    #         request_count = await self.__run_task(self._scheduler.get_total_request)
    #         self._logger.debug('Total Crawled {crawled_count} Pages, {item_count} Items; '
    #                            'Total {request_count} Requests in The {scheduler_name}',
    #                            crawled_count=self.__crawled_count__,
    #                            item_count=self.__item_count__,
    #                            request_count=request_count,
    #                            scheduler_name=self._scheduler.__class__.__name__)
    #         await asyncio.sleep(self.__log_interval__)

    def __shutdown_crawler(self, _, __):
        self.__signal_int_count += 1

        if self.__signal_int_count < 2:
            self._logger.debug('Received SIGNAL INT, shutting down gracefully. Send again to force')
            self.close_crawler('Shutdown')
        else:
            self.close_crawler('Shutdown by force', force=True)
            self._logger.debug('Received SIGNAL INT Over 2 times, shutting down the Crawler by force...')

    def close_crawler(self, reason: str = "Finished", force: bool = False):
        self.__job_scheduler.shutdown(force)
        self.__closed_reason = reason

    async def main(self):
        for target, args, kwargs in self.__pre_tasks:
            self.__job_scheduler.add_spawn_task(target, False, *args, **kwargs)
        self.__job_scheduler.add_spawn_task(self.__initialize)
        await self.__job_scheduler.run_tasks()

        for _ in range(self._settings.CONCURRENT_WORDS):
            self.__job_scheduler.add_spawn_task(self.__handle_word, True)

        for _ in range(self._settings.CONCURRENT_REQUESTS):
            self.__job_scheduler.add_spawn_task(self.__handle_request, True)

        # await self.__job_scheduler.add_spawn_task(self.__log, False)

        await self.__job_scheduler.run_tasks()

        for target, args, kwargs in self.__completed_tasks:
            self.__job_scheduler.add_spawn_task(target, False, *args, **kwargs)

        await self.__job_scheduler.run_tasks()

    def run(self):
        signal.signal(signal.SIGINT, self.__shutdown_crawler)

        try:
            # try import uvloop as Event Loop Policy

            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except:
            pass

        asyncio.run(self.main())
        self._logger.debug('The Crawler was closed: {reason}', reason=self.__closed_reason)
