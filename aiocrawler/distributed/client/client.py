# coding: utf-8
import asyncio
import aiojobs
from pathlib import Path
from ujson import loads
from shutil import unpack_archive
from typing import Optional, Dict
from aiohttp import ClientSession, CookieJar
from aiocrawler.engine import Engine
from aiocrawler.utils import get_setting, get_spider
from aiocrawler.distributed.common import SPIDER_DIR, scan_spider
from aiocrawler.distributed.client.client_collector import ClientCollector
from aiocrawler.distributed.client.connection import WebsocketConnection


class WebsocketClient(object):
    def __init__(self, server_host: str, port: Optional[int] = 8989):
        self._job_scheduler: aiojobs.Scheduler = None
        self._conn = WebsocketConnection(server_host=server_host, port=port)
        self._aiohttp_client_session: ClientSession = None

        self.__monitors: Dict[str, Monitor] = {}    # {spider_name: monitor}

    def run(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.main())
        finally:
            loop.close()

    async def close(self):
        if self._aiohttp_client_session:
            await self._aiohttp_client_session.close()
        if self._conn:
            await self._conn.close()

    async def main(self):
        try:
            self._job_scheduler = await aiojobs.create_scheduler(limit=None)
            await self._conn.connect()
            if self._conn.websocket is None:
                return

            await self._interactive_loop()
        finally:
            await self.close()

    async def _interactive_loop(self):
        async for msg in self._conn.websocket:
            # noinspection PyBroadException
            try:
                data = loads(msg.data)

                command = data.get('command', 0)
                if command == 1:
                    await self._job_scheduler.spawn(self.do_download_project(data))
                # elif command == 2:
                #     await self._job_scheduler.spawn(self.do_run(data))
                elif command == 3:
                    await self._job_scheduler.spawn(self.do_run_spider(data))
                elif command == 4:
                    await self._job_scheduler.spawn(self.do_stop_spider(data))
                elif command == 5:
                    await self._job_scheduler.spawn(self.do_update(data))
            except Exception:
                pass

    async def do_run_spider(self, data):
        monitor = Monitor(package=data['info']['package'],
                          spider_classname=data['info']['spider_classname'],
                          conn=self._conn,
                          job_scheduler=self._job_scheduler)
        self.__monitors[data['info']['spider_classname']] = monitor
        await monitor.main()

    async def do_stop_spider(self, data):
        classname = data['info']['spider_classname']
        if classname in self.__monitors:
            self.__monitors[classname].engine.close_crawler(reason='Stop spider by command')
            self.__monitors.pop(classname)

    async def do_download_project(self, data):
        if not self._aiohttp_client_session:
            await self.__create_aiohttp_client_session()

        url = data['info']['url']
        filename = Path(data['info']['filename'])
        project_dir = SPIDER_DIR / filename.stem
        project_dir.mkdir(exist_ok=True)
        try:
            async with self._aiohttp_client_session.get(url) as resp:
                content = await resp.read()

            with filename.open('wb') as fb:
                fb.write(content)

            unpack_archive(filename=filename, extract_dir=project_dir)

            await self._conn.send_json({
                'command': data['command'],
                'status': 0,
                'project_name': filename.stem,
                'msg': 'download successfully'
            }, classname=self.__class__.__name__)
        except Exception as e:
            await self._conn.send_json({
                'command': data['command'],
                'status': 100,
                'project_name': filename.stem,
                'error': str(e)
            }, classname=self.__class__.__name__)

    async def do_scan_spider(self, data):
        spiders = scan_spider()
        await self._conn.send_json({
            'command': data['command'],
            'status': 0,
            'spiders': spiders
        }, classname=self.__class__.__name__)

    async def do_update(self, data):
        pass

    async def __create_aiohttp_client_session(self):
        if not self._aiohttp_client_session:
            ck = CookieJar(unsafe=True)
            self._aiohttp_client_session = ClientSession(cookie_jar=ck)


class Monitor(object):
    def __init__(self, package: str,
                 spider_classname: str,
                 conn: WebsocketConnection = None,
                 job_scheduler: aiojobs.Scheduler = None,
                 server_host: str = None,
                 port: int = 8989):
        """
        :param package: package
        :param spider_classname: spider classname
        :param conn: WebsocketConnection
        :param job_scheduler: aiojobs.Scheduler
        :param server_host: server host
        :param port: server port
        """

        self.__package = package
        self.__spider_classname = spider_classname
        self.__conn = conn
        self.__job_scheduler = job_scheduler
        self.__server_host = server_host
        self.__port = port

        self.__collector: ClientCollector = None
        self.engine: Engine = None

    def run(self):
        pass

    async def main(self):
        try:
            await self.create_engine()
            await self.engine.main()
        except Exception as e:
            await self.__conn.send_json({
                'status': 1000,
                'error': str(e)
            }, classname=self.__class__.__name__)

    async def create_engine(self):
        settings = get_setting(module_name=''.join([self.__package, 'settings']))
        spider = get_spider(classname=self.__spider_classname, module_name='.'.join([self.__package, 'spiders']))

        if not settings or not spider:
            await self.__conn.send_json({
                'status': 100,
                'error': 'settings or spider name is not found'
            }, self.__class__.__name__)
            return
        settings = settings()
        spider = spider(settings=settings)
        self.engine = Engine(settings=settings,
                             spider=spider,
                             collector=self.__collector,
                             job_scheduler=self.__job_scheduler)


if __name__ == '__main__':
    from sys import path

    current = str(Path().parent.parent.parent.absolute())
    if current not in path:
        path.append(current)

    client = WebsocketClient('localhost')
    client.run()
