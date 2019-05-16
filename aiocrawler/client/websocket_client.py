# coding: utf-8
import sys
import aiojobs
from pathlib import Path
from ujson import loads, dumps
from typing import Optional, Union
from aiohttp import ClientSession, CookieJar
from aiocrawler.client.connection import WebsocketConnection


class WebsocketClient(object):
    def __init__(self, ip: str, port: Optional[int] = 8989, project_dir: Optional[Union[str, Path]] = None):
        self._ip = ip
        self._port = port
        self._project_dir = Path(project_dir) or Path()
        if str(self._project_dir) not in sys.path:
            sys.path.append(str(self._project_dir))

        self._job_scheduler: aiojobs.Scheduler = None
        self._conn = WebsocketConnection()
        self._ws = None
        self._aiohttp_client_session: ClientSession = None

    async def main(self):
        self._job_scheduler = await aiojobs.create_scheduler(limit=None, pending_limit=100000)
        self._ws = await self._conn.connect(self._ip, self._port)
        if self._ws is None:
            return

        await self._conn.close()

    async def _command_dispatch(self):
        async for msg in self._ws:
            # noinspection PyBroadException
            try:
                data = loads(msg.data)

                command = data.get('command', None)
                if command == 'download':
                    await self._job_scheduler.spawn(self._do_download_project(data))
                elif command == 'run':
                    pass
                elif command == 'stop':
                    pass
                elif command == 'update':
                    pass
            except Exception:
                pass

    async def _do_download_project(self, data: dict):
        if not self._aiohttp_client_session:
            await self.__create_aiohttp_client_session()

        url = data['info']['url']
        project_name = data['info']['project_name']
        formatter = data['info']['formatter']
        project_dir = self._project_dir / project_name

        try:
            project_dir.mkdir(exist_ok=True)

            filename = project_dir/'{name}.{suffix}'.format(name=project_name, suffix=formatter)

            async with self._aiohttp_client_session.get(url) as resp:
                content = await resp.read()

            with filename.open('wb') as fb:
                fb.write(content)

            await self.__send_json({
                'status': 0,
                'project_name': project_name,
                'msg': 'download successfully'
            })
        except Exception as e:
            await self.__send_json({
                'status': 100,
                'project_name': project_name,
                'msg': str(e)
            })

    async def _do_run(self, data: dict):
        from multiprocessing import Process
        project_name = data['info']['project_name']
        spider_name = data['info']['spider_name']
        setting_name = data['info'].get('setting_name', None)

    async def _do_stop(self, data: dict):
        pass

    async def _do_update(self, data: dict):
        pass

    async def __create_aiohttp_client_session(self):
        if not self._aiohttp_client_session:
            ck = CookieJar(unsafe=True)
            self._aiohttp_client_session = ClientSession(cookie_jar=ck)

    async def __send_json(self, info):
        data = {
            'uuid': self._conn.uuid,
            'from': self.__class__.__name__,
            'info': info
        }
        await self._ws.send_str(dumps(data))
