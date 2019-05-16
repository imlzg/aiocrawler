# coding: utf-8
import asyncio
import signal
import traceback
from inspect import iscoroutinefunction, isfunction
from random import uniform
from time import sleep
from typing import Iterator, List, Union

from aiocrawler import BaseSettings, Field, Item, Request, Response, Spider, logger
from aiocrawler.downloaders import BaseDownloader
from aiocrawler.filters import BaseFilter
from aiocrawler.job_scheduler import JobScheduler
from aiocrawler.schedulers import BaseScheduler
from aiocrawler.collectors.base_collector import BaseCollector


class Engine(object):
    """
    The Engine schedules all components.
    """

    def __init__(self, spider: Spider,
                 settings: BaseSettings,
                 filters: BaseFilter = None,
                 scheduler: BaseScheduler = None,
                 downloader: BaseDownloader = None,
                 collector: BaseCollector = None
                 ):

        self._spider = spider
        self._scheduler = scheduler
        self._settings = settings

        self.__collector = collector if collector else BaseCollector()

        self._filters = filters
        self.__middlewares = []
        self.__downloader: BaseDownloader = downloader

        self.__signal_int_count = 0

        self.__startup_tasks = []
        self.__completed_tasks = []

        self.__job_scheduler = JobScheduler(settings=self._settings)

    def on_startup(self, target, *args, **kwargs):
        # prevent adding new target after startup tasks has been done
        if self.__collector.done_startup_tasks:
            logger.error('startup tasks has been done')
            return
        self.__startup_tasks.append((target, args, kwargs))

    def on_cleanup(self, target, *args, **kwargs):
        self.__completed_tasks.append((target, args, kwargs))

    async def __run_task(self, task, background=False):
        # noinspection PyBroadException
        try:
            if asyncio.iscoroutine(task):
                if background:
                    task = await self.__job_scheduler.scheduler.spawn(task)
                else:
                    task = await task

            return task
        except Exception:
            logger.error(traceback.format_exc())

    async def __initialize(self):
        """
        Initialize all necessary components.
        """
        logger.debug('Initializing...')

        if not self.__downloader:
            from aiocrawler.downloaders.aio_downloader import AioDownloader
            self.__downloader = AioDownloader(self._settings)

        if not self._scheduler:
            if self._settings.REDIS_URL and not self._settings.DISABLE_REDIS:
                from aiocrawler.schedulers import RedisScheduler
                self._scheduler = RedisScheduler(settings=self._settings)
                await self._scheduler.create_redis_pool()

                if not self._filters:
                    from aiocrawler.filters import RedisFilter
                    self._filters = RedisFilter(self._settings, redis_pool=self._scheduler.redis_pool)

                self.on_cleanup(self._scheduler.close_redis_pool)

            else:
                from aiocrawler.schedulers import MemoryScheduler
                self._scheduler = MemoryScheduler(self._settings, self._spider)

        if not self._filters:
            if self._settings.REDIS_URL and not self._settings.DISABLE_REDIS:
                from aiocrawler.filters import RedisFilter
                self._filters = RedisFilter(self._settings, redis_pool=self._scheduler.redis_pool)
                await self._filters.create_redis_pool()
                self.on_cleanup(self._filters.close_redis_pool)

            else:
                from aiocrawler.filters import MemoryFilter
                self._filters = MemoryFilter(self._settings)

        from aiocrawler import middlewares

        for mw_name, key in self._settings.DEFAULT_MIDDLEWARES.items():
            if 0 <= key <= 1000 and mw_name in middlewares.__all__:
                self.__middlewares.append((getattr(middlewares, mw_name), key))

        for mw, key in self._settings.MIDDLEWARES:
            if 0 <= key <= 1000 and issubclass(middlewares.BaseMiddleware, mw):
                self.__middlewares.append((mw, key))
        self.__middlewares = sorted(self.__middlewares, key=lambda x: x[1])
        self.__middlewares = list(map(lambda x: x[0](self._settings, self), self.__middlewares))

        logger.debug('Initialized')

    async def __handle_downloader_output(self, request: Request, data: Union[Response, Exception, None]):
        """
        Handle the information returned by the downloader.
        :param request: Request
        :param data: Response or Exception
        """
        handled_data = None

        if isinstance(data, Exception):
            await self.__run_task(self.__collector.collect_downloader_exception(), background=True)
            handled_data = await self.__handle_downloader_exception(request, data)

        elif isinstance(data, Response):
            await self.__run_task(self.__collector.collect_response_received(response=data), background=True)
            handled_data = await self.__handle_downloader_response(request, data)

        if not handled_data:
            return
        if not isinstance(handled_data, Iterator) and not isinstance(handled_data, List):
            handled_data = [handled_data]

        tasks = []
        for one in handled_data:
            if isinstance(one, Request):
                if iscoroutinefunction(self._scheduler.send_request):
                    tasks.append(asyncio.ensure_future(self._scheduler.send_request(one)))
                else:
                    self._scheduler.send_request(one)
            elif isinstance(one, Item):
                item = await self.__handle_spider_item(one)
                if item:
                    tasks.append(asyncio.ensure_future(
                        self.__filter_and_send(request, item)))

        if len(tasks):
            await asyncio.wait(tasks)

    async def __handle_downloader_exception(self, request: Request, exception: Exception):
        handled_data = None
        for middleware in self.__middlewares:
            handled_data = await self.__run_task(middleware.process_exception(request, exception))
            if handled_data:
                break

        if handled_data is None:
            if isfunction(request.err_callback) and hasattr(self._spider.__class__, request.err_callback.__name__):
                handled_data = request.err_callback(request, exception)

        return handled_data

    async def __handle_downloader_response(self, request: Request, response: Response):
        handled_data = None
        response = self._spider.__parse_html__(request, response)
        for middleware in self.__middlewares:
            handled_data = await self.__run_task(middleware.process_response(request, response))
            if handled_data:
                if isinstance(handled_data, Response):
                    response = handled_data
                break

        if isinstance(handled_data, Response) or handled_data is None:
            logger.success('Crawled ({status}) <{method} {url}>',
                           status=response.status,
                           method=request.method,
                           url=request.url
                           )

            response.meta = request.meta
            if isfunction(request.callback) and hasattr(self._spider.__class__, request.callback.__name__):
                handled_data = request.callback(response)

        return handled_data

    async def __handle_spider_item(self, item: Item):
        for middleware in self.__middlewares:
            processed_item = await self.__run_task(middleware.process_item(item))
            if isinstance(processed_item, Item):
                item = processed_item
                break

        if item:
            item_copy = item.__class__()
            for field in self.get_fields(item):
                item_copy[field] = item.get(field, None)

            return item_copy

    async def __filter_and_send(self, request: Request, item: Item):
        item = await self.__run_task(self._filters.filter_item(item))
        if item:
            await self.__run_task(self.__collector.collect_item(item), background=True)

            logger.success('Crawled from <{method} {url}> \n {item}',
                           method=request.method, url=request.url, item=item)

            await self.__run_task(self._scheduler.send_item(item))

    @staticmethod
    def get_fields(item: Item):
        for field_name in item.__class__.__dict__:
            if isinstance(getattr(item.__class__, field_name), Field):
                yield field_name

    async def __handle_scheduler_word(self):
        """
        Handle the word from the scheduler.
        """
        word = await self.__run_task(self._scheduler.get_word())
        if word:
            await self.__run_task(self.__collector.collect_word(), background=True)

            logger.debug(
                'Making Request from word <word: {word}>'.format(word=word))
            request = self._spider.make_request(word)
            if request:
                await self.__run_task(self._scheduler.send_request(request))

    async def __handle_scheduler_request(self):
        """
        Handle the request from scheduler.
        """
        request = await self.__run_task(self._scheduler.get_request())
        if request:
            request = await self.__run_task(self._filters.filter_request(request))
            if request:
                await self.__run_task(self.__collector.collect_request(request), background=True)

                for downloader_middleware in self.__middlewares:
                    await self.__run_task(downloader_middleware.process_request(request))

                sleep(self._settings.DOWNLOAD_DALEY * uniform(0.5, 1.5))
                data = await self.__run_task(self.__downloader.download(request))
                await self.__handle_downloader_output(request, data)

    def __shutdown_crawler(self, _, __):
        self.__signal_int_count += 1

        if self.__signal_int_count == 1:
            logger.debug('Received SIGNAL INT, shutting down gracefully. Send again to force')
            self.close_crawler('Shutdown')
        else:
            self.close_crawler('Shutdown by force', force=True)
            logger.debug('Received SIGNAL INT Over 2 times, shutting down the Crawler by force...')

    def close_crawler(self, reason: str = "Finished", force: bool = False):
        self.__job_scheduler.shutdown(force)
        self.__collector.finish_reason = reason

    async def main(self):
        if self.__collector.running:
            logger.error('The Crawler already running')
            return

        for target, args, kwargs in self.__startup_tasks:
            self.__job_scheduler.add_spawn_task(target, False, *args, **kwargs)

        self.__job_scheduler.add_spawn_task(self.__initialize)
        await self.__job_scheduler.run_tasks()

        await self.__run_task(self.__collector.collect_start(
            self._spider.__class__.__name__, self._settings.DATETIME_FORMAT))

        for _ in range(self._settings.CONCURRENT_WORDS):
            self.__job_scheduler.add_spawn_task(self.__handle_scheduler_word, True)

        for _ in range(self._settings.CONCURRENT_REQUESTS):
            self.__job_scheduler.add_spawn_task(self.__handle_scheduler_request, True)

        await self.__job_scheduler.run_tasks()

        for target, args, kwargs in self.__completed_tasks:
            self.__job_scheduler.add_spawn_task(target, False, *args, **kwargs)

        await self.__job_scheduler.run_tasks()

        # collect finished information
        await self.__run_task(self.__collector.collect_finish(self._settings.DATETIME_FORMAT))

    def run(self):
        signal.signal(signal.SIGINT, self.__shutdown_crawler)

        # noinspection PyBroadException
        try:
            # try import uvloop as Event Loop Policy

            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except Exception:
            pass

        asyncio.run(self.main())
        self.__collector.output_stats()
        logger.debug('The Crawler was closed. <Reason {reason}>', reason=self.__collector.finish_reason)
