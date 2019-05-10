# coding: utf-8
import asyncio
from typing import Any, Callable, Dict, List, Tuple

import traceback

import aiojobs
from . import BaseSettings


class JobScheduler(object):
    def __init__(self, settings: BaseSettings = None,
                 event_interval=0.1,
                 check_done_fn=None, *args, **kwargs):

        self._settings = settings if settings else BaseSettings()
        self._logger = self._settings.LOGGER
        self.scheduler: aiojobs.Scheduler = None

        self.closing = False
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

    async def __check_done_count(self, target: Callable, *args, **kwargs):
        await target(*args, **kwargs)
        self._done_count += 1

    async def wait_for_done(self, fn, *args, **kwargs):
        if not callable(fn):
            def func(_=None, __=None):
                if self._done_count == self._running_task_count:
                    return True

            fn = func

        while True:
            if fn(*args, **kwargs):
                self._shutdown = True
                break
            await asyncio.sleep(self._event_interval)

    async def run_tasks(self):
        if not len(self._spawn_tasks):
            return

        if self.scheduler is None or self.scheduler.closed:
            self._shutdown = False
            self.closing = False
            self._done_count = 0
            await self.create_new_job_scheduler()

        self._running_task_count = len(self._spawn_tasks)
        while len(self._spawn_tasks):
            target, repeat, args, kwargs = self._spawn_tasks.pop()
            if repeat:
                await self.scheduler.spawn(self.__check_done_count(
                    self._repeat_running_until_received_closing, target, *args, **kwargs
                ))
            else:
                await self.scheduler.spawn(self.__check_done_count(target, *args, **kwargs))

        await self.scheduler.spawn(self.wait_for_done(self._check_done_fn, *self._args, **self._kwargs))

        while True:
            if self._shutdown:
                break
            await asyncio.sleep(self._event_interval)

        await self.scheduler.close()

    def shutdown(self, force=False):
        if force:
            self._shutdown = True
        else:
            self.closing = True

    async def _repeat_running_until_received_closing(self, fn: Callable, *args, **kwargs):
        try:
            while True:
                if self.closing:
                    break
                await asyncio.sleep(self._settings.PROCESS_DALEY)
                await fn(*args, **kwargs)
        except:
            self._logger.error(traceback.format_exc())
