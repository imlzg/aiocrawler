# coding: utf-8
import asyncio
from typing import Any, Callable, Dict, List, Tuple

import traceback

import aiojobs
from aiocrawler import BaseSettings, logger


class JobScheduler(object):
    def __init__(self, settings: BaseSettings = None,
                 event_interval=1,
                 scheduler: aiojobs.Scheduler = None,
                 check_done_fn=None, *args, **kwargs):

        self._settings = settings if settings else BaseSettings()
        self.scheduler: aiojobs.Scheduler = scheduler

        self.shutting_down = False
        self._shutdown = False
        self._done_count = 0

        self._event_interval = event_interval
        self._spawn_tasks: List[Tuple[Callable, bool, Tuple[Any], Dict[str, Any]]] = []
        self._running_task_count = 0

        self._check_done_fn = check_done_fn
        self._args = args
        self._kwargs = kwargs

    async def create_new_job_scheduler(self, loop: asyncio.AbstractEventLoop = None):
        if loop is None:
            loop = asyncio.get_event_loop()

        self.scheduler = aiojobs.Scheduler(close_timeout=self._settings.AIOJOBS_CLOSED_TIMEOUT,
                                           exception_handler=None,
                                           limit=self._settings.AIOJOBS_LIMIT,
                                           loop=loop, pending_limit=self._settings.AIOJOBS_LIMIT)

    def add_spawn_task(self, target: Callable, repeat: bool = False, *args, **kwargs):
        if callable(target):
            self._spawn_tasks.append((target, repeat, args, kwargs))

    async def __add_done_count(self, target: Callable, *args, **kwargs):
        await target(*args, **kwargs)
        self._done_count += 1

    async def wait_for_done(self):
        while True:
            if self._done_count == self._running_task_count:
                self._shutdown = True
                break
            await asyncio.sleep(self._event_interval)

    async def run_tasks(self):
        if not len(self._spawn_tasks):
            return

        if self.scheduler is None or self.scheduler.closed:
            self._shutdown = False
            self.shutting_down = False
            self._done_count = 0
            await self.create_new_job_scheduler()

        self._running_task_count = len(self._spawn_tasks)
        while len(self._spawn_tasks):
            target, repeat, args, kwargs = self._spawn_tasks.pop()
            if repeat:
                await self.scheduler.spawn(self.__add_done_count(
                    self._repeat_until_received_signal, target, *args, **kwargs
                ))
            else:
                await self.scheduler.spawn(self.__add_done_count(target, *args, **kwargs))

        await self.scheduler.spawn(self.wait_for_done())

        while True:
            if self._shutdown:
                break
            await asyncio.sleep(self._event_interval)

        await self.scheduler.close()

    def shutdown(self, force=False):
        if force:
            self._shutdown = True
        else:
            self.shutting_down = True

    async def _repeat_until_received_signal(self, fn: Callable, *args, **kwargs):
        # noinspection PyBroadException
        try:
            while True:
                if self.shutting_down:
                    break
                await asyncio.sleep(self._settings.PROCESS_DALEY)
                await fn(*args, **kwargs)
        except Exception:
            logger.error(traceback.format_exc())
