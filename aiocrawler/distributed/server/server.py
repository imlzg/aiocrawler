# coding: utf-8
import asyncio
import aiojobs
from aiohttp import web
from ujson import loads
from typing import Dict
from aiocrawler.distributed.server.admin import Admin
from aiocrawler.distributed.client.client_collector import ClientCollector
from aiocrawler.distributed.server.utils import login_required, json_or_jsonp_response, gen_uuid
from aiocrawler.distributed.server.model.client_model import ClientDatabase
from aiocrawler.distributed.server.model.task_model import TaskDatabase


class WebsocketServer(object):
    def __init__(self, job_scheduler: aiojobs.Scheduler, admin: Admin):
        self.__admin = admin
        self.__job_scheduler = job_scheduler
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

        self.__collector_keys = ClientCollector.get_collect_keys()
        self.__interval = 2

    def routes(self):
        return [
            web.get('/api/server/verify', self.verify_api, name='verify'),
            web.get('/api/server/unverified', self.unverified_api, name='unverified'),

            web.get('/api/server/connect/{token}/{uuid}/{session_id}', self.websocket, name='connect'),
            web.post('/api/server/get_connect_info', self.get_websocket_token, name='get_websocket_token'),

            web.get('/api/server/get_verified', self.get_verified_client_api, name='get_verified'),
            web.get('/api/server/get_unverified', self.get_unverified_client_api, name='get_unverified')

        ]

    async def websocket(self, request: web.Request):
        uuid = request.match_info.get('uuid', None)
        token = request.match_info.get('token', None)
        session_id = request.match_info.get('session_id', None)
        if self.client_db.verify(uuid, token) and session_id:
            websocket = web.WebSocketResponse()
            check = websocket.can_prepare(request)
            if check:
                await websocket.prepare(request)
                self.ws_client[uuid][session_id] = websocket
                await self.receive(websocket)
                self.ws_client[uuid].pop(session_id, None)
                if not websocket.closed:
                    await websocket.close()
                return websocket
        else:
            return web.HTTPNotFound()

    async def close_ws_client(self, _):
        """
        close websocket client on cleanup
        :param _:
        """
        for ws_list in self.ws_client.values():
            for ws in ws_list.values():
                if not ws.closed:
                    await ws.close()

    @login_required
    async def verify_api(self, request: web.Request):
        uuid = request.match_info.get('uuid', None)
        token = self.client_db.set_token(uuid)
        if token:
            return json_or_jsonp_response(request, {
                'status': 0,
                'msg': '"{uuid} is verified"'.format(uuid=uuid)
            })
        else:
            return json_or_jsonp_response(request, {
                'status': 101,
                'msg': 'uuid: {uuid} is not found'.format(uuid=uuid)
            })

    @login_required
    async def unverified_api(self, request: web.Request):
        uuid = request.match_info.get('uuid', None)
        check = self.client_db.clear_token(uuid)
        if check:
            return json_or_jsonp_response(request, {
                'status': 0,
                'msg': '{uuid}\'s token is cleared'.format(uuid=uuid)
            })
        else:
            return json_or_jsonp_response(request, {
                'status': 101,
                'msg': 'uuid: {uuid} is not found'.format(uuid=uuid)
            })

    @login_required
    async def get_unverified_client_api(self, request: web.Request):
        client_list = self.client_db.get_unverified_client()
        data = [{
            'uuid': client.uuid,
            'remote': client.remote_ip,
            'host': client.host,
            'hostname': client.hostname
        } for client in client_list]
        return json_or_jsonp_response(request, {
            'status': 0,
            'data': data
        })

    @login_required
    async def get_verified_client_api(self, request: web.Request):
        client_list = self.client_db.get_verified_client()
        data = [{
            'uuid': client.uuid,
            'remote': client.remote_ip,
            'host': client.host,
            'hostname': client.hostname,
            'token': client.token
        } for client in client_list]
        return json_or_jsonp_response(request, {
            'status': 0,
            'data': data
        })

    async def get_websocket_token(self, request: web.Request):
        data = await request.post()
        if 'host' in data and 'hostname' in data and request.remote:
            uuid = gen_uuid(request.remote, data['host'], data['hostname'])
            info = self.client_db.get_client_info(uuid)
            if info and info.token:
                return json_or_jsonp_response(request, {
                    'status': 0,
                    'uuid': uuid,
                    'token': info.token
                })
            else:
                await self.__job_scheduler.spawn(self.__admin.send_message({
                    'message': {
                        'title': 'Connection request',
                        'msg': 'There is a new request from {remote}'.format(remote=request.remote),
                        'url': str(request.app.router['connection'].url_for())
                    }
                }))

                self.client_db.create_client(request.remote, data['host'], data['hostname'])

        return json_or_jsonp_response(request, {
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

    async def crawler_info(self):
        connection_count = len(self.ws_client)
        crawler_count = self.client_db.get_verified_client_count()
        active_count = self.task_db.get_active_task_count()
        task_count = self.task_db.get_task_count()
        spider_count = 0
        for packages in self.__spiders.values():
            for package in packages.values():
                spider_count += package['spider_count']

        crawler_info = {
            'connection-count': connection_count,
            'crawler-count': crawler_count,
            'active-count': active_count,
            'task-count': task_count,
            'spider-count': spider_count
        }
        await self.__admin.send_message({'crawler_info': crawler_info})
