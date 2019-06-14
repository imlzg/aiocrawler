# coding: utf-8
import re
import asyncio
import aiojobs
import aiohttp_jinja2
from aiohttp import web
from ujson import loads
from typing import Dict, Union
from time import time
from pathlib import Path
from datetime import datetime
from aiohttp_session import get_session
from aiocrawler.distributed.server.admin import Admin
from aiocrawler.distributed.common import scan
from aiocrawler.distributed.server.utils import gen_token
from aiocrawler.distributed.client.client_collector import ClientCollector
from aiocrawler.distributed.server.utils import login_required, jsonp_response, gen_uuid, DATETIME_FORMAT
from aiocrawler.distributed.server.model.client_model import ClientDatabase
from aiocrawler.distributed.server.model.task_model import TaskDatabase


class WebsocketServer(object):
    def __init__(self, job_scheduler: aiojobs.Scheduler, admin: Admin, project_dir: Union[str, Path]):
        self.__admin = admin
        self.__job_scheduler = job_scheduler
        self.__project_dir = Path(project_dir)

        self.client_db = ClientDatabase()
        self.task_db = TaskDatabase()

        # ws_client: {uuid: {session_id: websocket}}
        self.ws_client = {}

        '''spiders:
        {uuid:
            {package: {
                'spider_count': count,
                'spiders': {
                    spider_name: spider_classname
                },
                'files': {
                    filename: hash
                },
                'created_at': time,
                'updated_at': time
            }}
        }'''
        self.__spiders: Dict[str, Dict[str, Dict]] = {}

        '''tasks:
            {uuid: {
                task_id: {
                    'items': items,
                    'changed': False
                }
            }}
        '''
        self.__tasks: Dict[str, Dict[str, Dict]] = {}

        self.__blacklist: Dict[str, int] = {}
        self.__ban_time = 60 * 30

        self.__collector_keys = ClientCollector.get_collect_keys()
        self.__interval = 2

        self.__verified_clients = self.client_db.get_verified_client()
        self.__unverified_clients = self.client_db.get_unverified_client()
        self.__project_count = 0

        self.__paginate_by = 5

        self.__ip_pattern = r'(?=(\b|\D))(((\d{1,2})|(1\d{1,2})'
        self.__ip_pattern += r'|(2[0-4]\d)|(25[0-5]))\.){3}((\d{1,2})|(1\d{1,2})|(2[0-4]\d)|(25[0-5]))(?=(\b|\D))'

    def routes(self):
        return [
            web.get('/api/server/auth/{id}', self.auth_api, name='verify'),
            web.get('/api/server/deauth/{id}', self.deauth_api, name='unverified'),

            web.get('/api/server/connect/{uuid}/{token}/{session_id}', self.connect_to_websocket, name='connect'),
            web.get('/api/server/get_connection_info/{host}/{hostname}',
                    self.get_websocket_token, name='get_websocket_token'),

            web.get('/api/server/get_verified', self.get_verified_client_api, name='get_verified'),
            web.get('/api/server/get_unverified', self.get_unverified_client_api, name='get_unverified'),

            web.get('/api/server/put_into_blacklist/{remote}', self.put_into_blacklist, name='put'),
            web.get('/api/server/remove_remote_from_blacklist/{remote}', self.remove_remote_from_blacklist,
                    name='remove'),

            web.get('/api/server/remove_client/{id}', self.remove_client_api, name='remove_client'),

            web.get('/api/server/get_project', self.get_project, name='get_project'),
            web.post('/api/server/upload', self.upload, name='upload'),

            web.get('/api/server/get_info', self.get_info, name='get_info'),
            web.get('/api/server/get_header', self.get_header, name='get_header'),

        ]

    def is_ban(self, remote: str):
        if remote in self.__blacklist and time() - self.__blacklist[remote] <= self.__ban_time:
            return True

    async def connect_to_websocket(self, request: web.Request):
        if self.is_ban(request.remote):
            return web.HTTPNotFound()

        uuid = request.match_info.get('uuid', None)
        token = request.match_info.get('token', None)
        session_id = request.match_info.get('session_id', None)
        if self.client_db.verify(uuid, token) and session_id:
            websocket = web.WebSocketResponse()
            check = websocket.can_prepare(request)
            if check:
                await websocket.prepare(request)
                if uuid not in self.ws_client:
                    self.ws_client[uuid] = {}
                self.ws_client[uuid][session_id] = websocket
                self.client_db.set_status(uuid=uuid, status=1)
                await self.receive(websocket)
                self.ws_client[uuid].pop(session_id, None)
                self.client_db.set_status(uuid=uuid, status=0)
                return websocket

    async def close_ws_client(self, _):
        """
        close websocket client on cleanup
        :param _:
        """
        for uuid, ws_list in self.ws_client.items():
            for ws in ws_list.values():
                if not ws.closed:
                    await ws.close()
                    self.client_db.set_status(uuid=uuid, status=0)

    @login_required
    async def auth_api(self, request: web.Request):
        client_id = request.match_info.get('id', None)
        token = self.client_db.auth(client_id)
        if token:
            return jsonp_response(request, {
                'status': 0,
                'msg': '"id: {client_id} is verified"'.format(client_id=client_id)
            })
        else:
            return jsonp_response(request, {
                'status': 101,
                'msg': 'id: {client_id} is not found'.format(client_id=client_id)
            })

    @login_required
    async def deauth_api(self, request: web.Request):
        uuid = request.match_info.get('uuid', None)
        check = self.client_db.clear_token(uuid)
        if check:
            return jsonp_response(request, {
                'status': 0,
                'msg': '{uuid}\'s token is cleared'.format(uuid=uuid)
            })
        else:
            return jsonp_response(request, {
                'status': 101,
                'msg': 'uuid: {uuid} is not found'.format(uuid=uuid)
            })

    @login_required
    async def remove_client_api(self, request: web.Request):
        client_id = request.match_info.get('id', None)
        if client_id:
            result = self.client_db.remove_client(client_id)
            if result:
                return jsonp_response(request, {
                    'status': 101,
                    'msg': result
                })
            else:
                return jsonp_response(request, {
                    'status': 0,
                    'msg': 'Delete the id: {client_id} successfully'.format(client_id=client_id)
                })
        else:
            return jsonp_response(request, {
                'status': 404,
                'msg': 'id is none'
            })

    @login_required
    async def get_unverified_client_api(self, request: web.Request):
        page_number = int(request.query.get('pageNumber', '1'))
        page_size = int(request.query.get('pageSize', '5'))

        total = self.__unverified_clients.count()
        # total = int(ceil(self.__unverified_clients.count() / page_size))
        rows = [{
            'id': one.client_id,
            'uuid': one.uuid,
            'remote': one.remote_ip,
            'host': one.host,
            'hostname': one.hostname,
            'last': one.connected_at.strftime(DATETIME_FORMAT)
        } for one in self.__unverified_clients.paginate(page_number, page_size)]

        return jsonp_response(request, {
            'total': total,
            'rows': rows
        })

    @login_required
    async def get_verified_client_api(self, request: web.Request):
        page_number = int(request.query.get('pageNumber', '1'))
        page_size = int(request.query.get('pageSize', '5'))

        total = self.__verified_clients.count()
        rows = [{
            'id': one.client_id,
            'uuid': one.uuid,
            'remote': one.remote_ip,
            'host': one.host,
            'hostname': one.hostname,
            'status': one.status,
            'authorized_at': one.authorized_at.strftime(DATETIME_FORMAT)

        } for one in self.__verified_clients.paginate(page_number, page_size)]

        return jsonp_response(request, {
            'total': total,
            'rows': rows
        })

    @login_required
    async def get_project(self, request: web.Request):
        projects = scan(project_dir=self.__project_dir)
        self.__project_count = len(projects)

        return jsonp_response(request, {
            'total': len(projects),
            'rows': projects
        })

    @login_required
    async def upload(self, request: web.Request):
        reader = await request.multipart()

        field = await reader.next()
        if field.name not in ['zip', 'tar']:
            return jsonp_response(request, {'success': 0, 'error': 'Invalid file type'})

        filename = field.filename
        filename = self.__project_dir/filename
        while filename.is_file():
            filename = self.__project_dir/(gen_token() + field.filename)

        with filename.open('wb') as fb:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                fb.write(chunk)

        return jsonp_response(request, {'success': 1})

    @login_required
    async def get_info(self, request: web.Request):
        return jsonp_response(request, {
            'status': 0,
            'connection_count': self.__unverified_clients.count(),
            'crawler_count': self.__verified_clients.count(),
            'project_count': self.__project_count,
            'task_count': 0
        })

    @login_required
    async def get_header(self, request: web.Request):
        session = await get_session(request)
        header = aiohttp_jinja2.render_template('header.html', request, {
            'username': session['username'],
            'connection_count': self.__unverified_clients.count(),
            'crawler_count': self.__verified_clients.count(),
            'project_count': self.__project_count,
            'task_count': 0
        }).body.decode()
        return jsonp_response(request, {
            'status': 0,
            'header': header
        })

    @login_required
    async def put_into_blacklist(self, request: web.Request):
        remote_host = request.match_info.get('remote')

        if remote_host in self.__blacklist:
            return jsonp_response(request, {
                'status': 1,
                'start_time': self.__blacklist[remote_host],
                'msg': '{remote} has been banned'.format(remote=remote_host)
            })

        self.__blacklist[remote_host] = int(time())
        return jsonp_response(request, {
            'status': 0,
            'start_time': datetime.fromtimestamp(self.__blacklist[remote_host]).strftime(DATETIME_FORMAT),
            'msg': '{remote} is banned'.format(remote=remote_host)
        })

    @login_required
    async def remove_remote_from_blacklist(self, request: web.Request):
        remote_ip = request.match_info.get('remote')
        if remote_ip in self.__blacklist:
            self.__blacklist.pop(remote_ip)
            return jsonp_response(request, {
                'status': 0,
            })
        else:
            return jsonp_response(request, {
                'status': 100,
                'msg': '{remote} is not found'.format(remote=remote_ip)
            })

    async def get_websocket_token(self, request: web.Request):
        if self.is_ban(request.remote) or 'host' not in request.match_info \
                or 'hostname' not in request.match_info or not re.match(self.__ip_pattern, request.match_info['host']):
            return web.HTTPNotFound()

        uuid = gen_uuid(request.remote, request.match_info['host'], request.match_info['hostname'])
        info = self.client_db.get_client_info(uuid)
        if info and info.token:
            return jsonp_response(request, {
                'status': 0,
                'uuid': uuid,
                'token': info.token
            })
        elif info:
            self.client_db.update(uuid)
        else:
            self.__admin.messages.append({
                    'title': 'Connection request',
                    'msg': 'There is a new request from {remote}'.format(remote=request.remote),
                    'url': str(request.app.router['connection'].url_for())
                })

            self.client_db.create_client(uuid,
                                         request.remote,
                                         request.match_info['host'],
                                         request.match_info['hostname'])
            self.__unverified_clients = self.client_db.get_unverified_client()

        return jsonp_response(request, {
            'status': 1001,
            'msg': 'Waiting for verification...'
        })

    async def receive(self, websocket: web.WebSocketResponse):
        async for msg in websocket:
            # noinspection PyBroadException
            try:
                data = loads(msg.data)
                if data['classname'] == 'ClientCollector':
                    await self.__job_scheduler.spawn(self.__handle_client_collector(data))
                elif data['classname'] == 'WebsocketClient':
                    await self.__job_scheduler.spawn(self.__handle_websocket_client(data))
                elif data['classname'] == 'Monitor':
                    await self.__job_scheduler.spawn(self.__handle_monitor(data))
            except Exception:
                pass

    async def __handle_client_collector(self, data: dict):
        if data['uuid'] not in self.__tasks or data['session_id'] not in self.__tasks[data['uuid']]:
            self.__tasks[data['uuid']] = {data['session_id']: {}}
        for key, value in data['info'].items():
            if key in self.__collector_keys:
                self.__tasks[data['uuid']][data['session_id']][key] = value

    async def insert(self):
        while True:
            for uuid, task in self.__tasks.items():
                for session_id, items in task.items():
                    self.task_db.replace(uuid, session_id, items)

            self.__tasks = {}
            await asyncio.sleep(self.__interval)

    async def __handle_websocket_client(self, data: dict):
        if data['info']['command'] == 1:
            pass

    async def __handle_monitor(self, data: dict):
        pass

    async def get_crawler_list(self):
        crawler_list = self.client_db.get_verified_client()
        return crawler_list
