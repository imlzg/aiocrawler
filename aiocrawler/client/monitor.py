# coding: utf-8
import asyncio
import aiojobs
from typing import Optional
from ujson import loads
from aiocrawler.engine import Engine
from aiocrawler.utils import get_setting, get_spider
from aiocrawler.client.connection import WebsocketConnection
from aiocrawler.client.client_collector import ClientCollector


class Monitor(object):
    def __init__(self,
                 project_name: str,
                 spider_name: str,
                 setting_name: str,
                 server_host: str,
                 port: Optional[int] = 8989):

        self._project_name = project_name
        self._spider_name = spider_name
        self.setting_name = setting_name
        self._server_host = server_host
        self._server_port = port

        self._conn = WebsocketConnection()

        self._collector: ClientCollector = None

        self._engine: Engine = None
        self._job_scheduler: aiojobs.Scheduler = None

    def run(self):
        # noinspection PyBroadException
        try:
            # try import uvloop as Event Loop Policy

            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except Exception:
            pass
        asyncio.run(self._run())

    async def _run(self):
        self._job_scheduler = await aiojobs.create_scheduler(limit=None)
        await self._create_engine()
        await self._interactive_loop()

    async def _create_engine(self):
        await self._conn.connect(self._server_host, self._server_port)
        if not self._conn.websocket:
            return

        self._collector = ClientCollector(connection=self._conn)

        settings = get_setting(module_name='{}.settings'.format(self._project_name))
        spider = get_spider(spider_name=self._spider_name, module_name='{}.spiders'.format(self._project_name))

        if not settings or not spider:
            await self._conn.send_json({
                'status': 100,
                'msg': 'settings or spider name is not found'
            })
            return
        settings = settings()
        spider = spider(settings=settings)
        self._engine = Engine(settings=settings,
                              spider=spider,
                              collector=self._collector,
                              job_scheduler=self._job_scheduler)

    async def _interactive_loop(self):
        async for msg in self._conn.websocket:
            data = loads(msg.data)
            command = data.get('command', None)
            if command == 'stop':
                self._engine.close_crawler(reason='Stop spider from {server}\' command: "stop"'.format(
                    server=self._server_host))
            elif command == 'start':
                await self._job_scheduler.spawn(self._engine.main())
