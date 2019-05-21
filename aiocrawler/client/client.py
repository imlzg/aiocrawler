# coding: utf-8
import sys
import aiojobs
from pathlib import Path
from ujson import loads
from typing import Optional, Union
from aiohttp import ClientSession, CookieJar
from aiocrawler.client.connection import WebsocketConnection


class WebsocketClient(object):
    def __init__(self, server_host: str, port: Optional[int] = 8989, root_dir: Optional[Union[str, Path]] = None):
        self._server_host = server_host
        self._port = port
        self._root_dir = Path(root_dir) or Path()
        if str(self._root_dir) not in sys.path:
            sys.path.append(str(self._root_dir))

        self._job_scheduler: aiojobs.Scheduler = None
        self._conn = WebsocketConnection()
        self._aiohttp_client_session: ClientSession = None

    async def main(self):
        self._job_scheduler = await aiojobs.create_scheduler(limit=None)
        await self._conn.connect(self._server_host, self._port)
        if self._conn.websocket is None:
            return

        await self._conn.close()

    async def _interactive_loop(self):
        async for msg in self._conn.websocket:
            # noinspection PyBroadException
            try:
                data = loads(msg.data)

                command = data.get('command', None)
                if command == 'download':
                    await self._job_scheduler.spawn(self.do_download_project(data))
                elif command == 'run':
                    await self._job_scheduler.spawn(self.do_run(data))
                elif command == 'update':
                    pass
            except Exception:
                pass

    async def do_download_project(self, data: dict):
        if not self._aiohttp_client_session:
            await self.__create_aiohttp_client_session()

        url = data['info']['url']
        project_name = data['info']['project_name']
        formatter = data['info']['formatter']
        project_dir = self._root_dir / project_name

        try:
            project_dir.mkdir(exist_ok=True)
            filename = project_dir/'{name}.{suffix}'.format(name=project_name, suffix=formatter)

            async with self._aiohttp_client_session.get(url) as resp:
                content = await resp.read()

            with filename.open('wb') as fb:
                fb.write(content)

            await self._conn.send_json({
                'status': 0,
                'project_name': project_name,
                'msg': 'download successfully'
            })
        except Exception as e:
            await self._conn.send_json({
                'status': 100,
                'project_name': project_name,
                'msg': str(e)
            })

    async def do_run(self, data: dict):
        from multiprocessing import Process
        project_name = data['info']['project_name']
        spider_name = data['info']['spider_name']
        setting_name = data['info'].get('setting_name', None)
        p = Process(target=self._run_spider, args=(project_name, spider_name, setting_name))
        p.start()

    async def do_update(self, data: dict):
        pass

    async def __create_aiohttp_client_session(self):
        if not self._aiohttp_client_session:
            ck = CookieJar(unsafe=True)
            self._aiohttp_client_session = ClientSession(cookie_jar=ck)

    def _run_spider(self, project_name: str, spider_name: str, setting_name: str):
        from aiocrawler.client.monitor import Monitor

        monitor = Monitor(project_name, spider_name, setting_name, self._server_host, self._port)
        monitor.run()
