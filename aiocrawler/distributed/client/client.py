# coding: utf-8
import asyncio
import aiojobs
from pathlib import Path
from ujson import loads
from shutil import unpack_archive
from typing import Optional, Dict, Union
from aiohttp import ClientSession, CookieJar
from aiocrawler.engine import Engine
from aiocrawler.log import logger
from aiocrawler.distributed.common import scan, ProjectScanner
from aiocrawler.utils import get_setting, get_spider
from aiocrawler.distributed.client.client_collector import ClientCollector
from aiocrawler.distributed.client.connection import WebsocketConnection


class WebsocketClient(object):
    def __init__(self, server_host: str,
                 port: Optional[int] = 8989,
                 project_dir: Union[str, Path] = None,
                 minitor_interval: int = 60):
        self._job_scheduler: aiojobs.Scheduler = None
        self.connection = WebsocketConnection(server_host=server_host, port=port)
        self._aiohttp_client_session: ClientSession = None

        self.__project_dir = project_dir if project_dir else Path('projects')
        self.__monitors: Dict[str, Monitor] = {}    # {spider_name: monitor}

        self.__last_changed: Dict[str, str] = {}
        self.__monitor_interval = minitor_interval
        self.__project_scanner = ProjectScanner(project_dir=self.__project_dir)

    def run(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.main())
        finally:
            loop.close()

    async def close(self):
        if self._aiohttp_client_session:
            await self._aiohttp_client_session.close()
        if self.connection:
            await self.connection.close()
        if not self._job_scheduler.closed:
            await self._job_scheduler.close()

    async def main(self):
        try:
            self._job_scheduler = await aiojobs.create_scheduler(limit=None)
            await self.connection.connect()
            if not self.connection.connected:
                return

            await self._job_scheduler.spawn(self.project_monitor())
            await self._interactive_loop()
            logger.debug('Disconnect from the server "{host}:{port}"'.format(host=self.connection.server_host,
                                                                             port=self.connection.port))
        finally:
            await self.close()

    async def _interactive_loop(self):
        logger.debug('start interactive loop...')
        async for msg in self.connection.websocket:
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
                elif command == 6:
                    # await self.do_scan(data)
                    pass
            except Exception:
                pass

    async def do_run_spider(self, data):
        monitor = Monitor(package=data['info']['package'],
                          spider_classname=data['info']['spider_classname'],
                          conn=self.connection,
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

        token = data['info']['token']
        filename = data['info']['filename']
        try:
            url = 'http://{host}:{port}/api/server/project/download/{token}'.format(
                host=self.connection.server_host,
                port=self.connection.port,
                token=token
            )
            async with self._aiohttp_client_session.get(url) as resp:
                content = await resp.read()

            with open(filename, 'wb') as fb:
                fb.write(content)

            unpack_archive(filename=filename, extract_dir=str(self.__project_dir/Path(filename).stem.split('_', 2)[-1]))
            Path(filename).unlink()

            await self.connection.send_json({
                'command': data['command'],
                'status': 0,
                'filename': filename
            }, classname='client')
        except Exception as e:
            await self.connection.send_json({
                'command': data['command'],
                'status': 100,
                'filename': filename,
                'error': str(e)
            }, classname='client')

    async def project_monitor(self):
        while True:
            changed = self.__project_scanner.scan()
            if changed:
                await self.connection.send_json({
                    'classname': 'client',
                    'command': 6,
                    'status': 0,
                    'projects': changed
                })
            await asyncio.sleep(self.__monitor_interval)

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
        settings = get_setting(module=''.join([self.__package, 'settings']))
        spider = get_spider(classname=self.__spider_classname, module='.'.join([self.__package, 'spiders']))

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
