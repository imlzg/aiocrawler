# coding: utf-8
import re
import asyncio
import aiojobs
import shutil
import aiohttp_jinja2
from aiohttp import web
from ujson import loads, dumps
from typing import Dict, Union, Set
from time import time
from pathlib import Path
from datetime import datetime
from aiocrawler import logger
from aiohttp_session import get_session
from aiocrawler.distributed.server.admin import Admin
from aiocrawler.distributed.common import scan
from aiocrawler.distributed.client.client_collector import ClientCollector
from aiocrawler.distributed.server.utils import login_required, jsonp_response, gen_uuid, DATETIME_FORMAT, gen_token
from aiocrawler.distributed.server.model.client_model import ClientDatabase
from aiocrawler.distributed.server.model.task_model import TaskDatabase


class WebsocketServer(object):
    def __init__(self, job_scheduler: aiojobs.Scheduler,
                 admin: Admin,
                 project_dir: Union[str, Path],
                 support_upload_types: Set[str] = None,
                 archive_type: str = 'tar'):

        self.__admin = admin
        self.__job_scheduler = job_scheduler
        self.__project_dir = Path(project_dir)

        self.__support_upload_types = support_upload_types \
            if support_upload_types else ('.zip', '.tar', '.tar.gz', '.tar.xz', '.tar.bz')

        self.client_db = ClientDatabase()
        self.client_db.init_status()

        self.task_db = TaskDatabase()

        self.__tasks = self.task_db.get_all_task()
        self.__tasks_tmp = []

        # ws_client: {uuid: {session_id: websocket}}
        self.ws_client = {}

        self.__blacklist: Dict[str, int] = {}
        self.__ban_time = 60 * 30

        self.__collector_keys = ClientCollector.get_collect_keys()
        self.__interval = 2

        self.__verified_clients = self.client_db.get_verified_client()
        self.__unverified_clients = self.client_db.get_unverified_client()
        self.__active_clients = self.client_db.get_active_client()

        self.__projects = scan(self.__project_dir)

        self.__client_projects: Dict[str, Dict] = {}

        self.__paginate_by = 5
        self.__archive_type = archive_type
        self.__downloads: Dict[str, str] = {}

        self.__ip_pattern = r'(?=(\b|\D))(((\d{1,2})|(1\d{1,2})'
        self.__ip_pattern += r'|(2[0-4]\d)|(25[0-5]))\.){3}((\d{1,2})|(1\d{1,2})|(2[0-4]\d)|(25[0-5]))(?=(\b|\D))'

    def routes(self):
        return [

            web.get('/api/server/connect/uuid/{uuid}/token/{token}',
                    self.websocket, name='connect'),
            web.get('/api/server/get_connection_info/host/{host}/hostname/{hostname}',
                    self.get_websocket_token, name='get_websocket_token'),

            web.get('/api/server/crawler/verified_list', self.get_verified_client_api, name='get_verified'),
            web.get('/api/server/crawler/active_list', self.get_active_client, name='get_active_client'),
            web.get('/api/server/crawler/deauth/{id}', self.deauth_api, name='deauth'),
            web.get('/api/sever/crawler/get_project/{uuid}', self.get_client_project, name='get_client_project'),

            web.get('/api/server/connection/list', self.get_unverified_client_api, name='get_unverified'),
            web.get(r'/api/server/connection/auth/{id:\d+}', self.auth_api, name='auth'),
            web.get(r'/api/server/connection/remove/{uuid}', self.remove_client_api, name='connection_remove'),

            web.get('/api/server/blacklist/put/{remote}', self.put_into_blacklist, name='put_into_blacklist'),
            web.get('/api/server/blacklist/remove/{remote}', self.remove_remote_from_blacklist,
                    name='remove_from_blacklist'),

            web.post('/api/server/project/upload', self.upload, name='upload'),
            web.get('/api/server/project/list', self.get_project, name='project_list'),
            web.get('/api/server/project/remove', self.remove_project, name='remove_project'),
            web.get('/api/server/project/deploy/name/{project_name}/uuid/{uuid}', self.deploy, name='deploy'),
            web.get('/api/server/project/download/{token}', self.download, name='download'),
            web.get('/server/project/edit', self.edit, name='edit'),

            web.get('/api/server/task/list', self.get_task, name='task_list'),

            web.get('/api/server/get_info', self.get_info, name='get_info'),
            web.get('/api/server/get_header', self.get_header, name='get_header'),

        ]

    def is_ban(self, remote: str):
        if remote in self.__blacklist:
            if time() - self.__blacklist[remote] <= self.__ban_time:
                return True
            self.__blacklist.pop(remote)

    async def websocket(self, request: web.Request):
        if self.is_ban(request.remote):
            return web.HTTPNotFound()

        uuid = request.match_info['uuid']
        token = request.match_info['token']
        if self.client_db.verify(uuid, token):
            websocket = web.WebSocketResponse()
            check = websocket.can_prepare(request)
            if check:
                await websocket.prepare(request)

                if uuid not in self.ws_client:
                    session_id = 'main'
                    self.ws_client[uuid] = {session_id: websocket}
                else:
                    session_id = gen_token()
                    self.ws_client[uuid][session_id] = websocket

                self.client_db.set_status(uuid=uuid, status=1)
                self.__admin.messages.append({
                    'msg': 'a client connected to the server'.format(uuid=uuid),
                    'type': 'success',
                    'url': str(request.app.router['crawler'].url_for())
                })

                await self.receive(websocket, uuid=uuid)
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

    @login_required
    async def auth_api(self, request: web.Request):
        client_id = request.match_info['id']
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
        uuid = request.match_info['uuid']
        check = self.client_db.clear_token(uuid)
        if check:
            return jsonp_response(request, {
                'status': 0,
                'msg': '{uuid}\'s token is cleared'.format(uuid=uuid)
            })
        else:
            return jsonp_response(request, {
                'status': 101,
                'msg': 'uuid: {uuid} not found'.format(uuid=uuid)
            })

    @login_required
    async def remove_client_api(self, request: web.Request):
        uuid = request.match_info['uuid']
        exception = self.client_db.remove_client(uuid)
        if exception:
            return jsonp_response(request, {
                'status': 400,
                'msg': exception
            })
        else:
            await self._disconnect_websocket(uuid)
            return jsonp_response(request, {
                'status': 0,
                'msg': 'Delete the uuid "{uuid}..." successfully'.format(uuid=uuid[:5])
            })

    async def _disconnect_websocket(self, uuid: str):
        if uuid in self.ws_client:
            for websocket in self.ws_client.pop(uuid).values():
                await websocket.close()

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
    async def get_active_client(self, request: web.Request):
        page_number = int(request.query.get('pageNumber', '1'))
        page_size = int(request.query.get('pageSize', '5'))

        total = self.__active_clients.count()
        rows = [{
            'id': one.client_id,
            'uuid': one.uuid,
            'remote': one.remote_ip,
            'host': one.host,
            'hostname': one.hostname,
            'status': one.status,
            'authorized_at': one.authorized_at.strftime(DATETIME_FORMAT)

        } for one in self.__active_clients.paginate(page_number, page_size)]

        return jsonp_response(request, {
            'total': total,
            'rows': rows
        })

    @login_required
    async def deploy(self, request: web.Request):
        project_name = request.match_info['project_name']
        uuid = request.match_info['uuid']
        filepath = self.__project_dir/project_name
        if project_name not in self.__projects or not filepath.is_dir():
            return jsonp_response(request, {
                'status': 400,
                'msg': 'project "{project_name}" is not found'.format(project_name=project_name)
            })
        elif uuid not in self.ws_client:
            return jsonp_response(request, {
                'status': 400,
                'msg': 'the crawler is disconnected'
            })

        archive = self.__projects[project_name].get('archive', None)
        if archive is None \
                or archive.split('_', 2)[0] != self.__projects[project_name]['hash'] \
                or not Path(archive).is_file():

            archive = shutil.make_archive(
                base_name='{project_dir}/{hash}_{project_name}'.format(
                    project_dir=str(self.__project_dir),
                    hash=self.__projects[project_name]['hash'], project_name=project_name),
                format=self.__archive_type,
                root_dir=str(filepath.absolute())
            )
            self.__projects[project_name]['archive'] = archive

        token = gen_token()
        while token in self.__downloads:
            token = gen_token()
        self.__downloads[token] = archive

        await self.send_command(uuid, 1, {'token': token, 'filename': Path(archive).name})
        return jsonp_response(request, {
            'status': 0,
        })

    async def download(self, request: web.Request):
        token = request.match_info['token']
        archive = self.__downloads.pop(token, None)
        if archive is None or not Path(archive).is_file():
            return web.HTTPNotFound()

        return web.FileResponse(path=archive)

    @login_required
    async def get_project(self, request: web.Request):
        return jsonp_response(request, {
            'total': len(self.__projects),
            'rows': list(self.__projects.values())
        })

    @login_required
    async def remove_project(self, request: web.Request):
        project_name = request.match_info['project_name']
        project = self.__projects.pop(project_name, None)
        if project:
            return jsonp_response(request, {'status': 0, 'msg': 'Remove {name} successfully'.format(name=project_name)})
        else:
            return jsonp_response(request,
                                  {'status': 400,
                                   'msg': 'project "{name}" not found'.format(name=project_name)
                                   }, status=400)

    @login_required
    async def upload(self, request: web.Request):
        reader = await request.multipart()

        field = await reader.next()
        if not field.filename.endswith(self.__support_upload_types):
            return jsonp_response(request, {'status': 'error', 'message': 'Invalid file type'}, status=400)

        self.__project_dir.mkdir(exist_ok=True)
        filename = self.__project_dir/field.filename
        with filename.open('wb') as fb:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                fb.write(chunk)

        status = self.add_project(filename)
        if status == 0:
            return jsonp_response(request,
                                  {'status': 'error',
                                   'message': 'The compressed file does not have a spider'
                                   }, status=400)
        elif status == 1:
            return jsonp_response(request,
                                  {'status': 'error',
                                   'message': 'The file already exists'
                                   }, status=400)
        else:
            return jsonp_response(request, {'status': 'ok'})

    def add_project(self, filename: Path):
        tmp_dir = self.__project_dir/gen_token()
        while tmp_dir.is_dir():
            tmp_dir = self.__project_dir/gen_token()

        shutil.unpack_archive(str(filename), extract_dir=str(tmp_dir))
        filename.unlink()

        status = 0
        idx = 1
        projects = scan(tmp_dir)
        hash_set = set(project['hash'] for project in self.__projects.values())
        for project_name, project in projects.items():
            if project['hash'] in hash_set:
                status = 1
                continue

            if project_name in self.__projects:
                name = '{name}_{idx}'.format(name=project_name, idx=idx)
                while name in self.__projects or (self.__project_dir/name).is_dir():
                    idx += 1
                    name = '{name}_{idx}'.format(name=project_name, idx=idx)
            elif project_name == tmp_dir.name:
                name = filename.stem
                while name in self.__projects or (self.__project_dir/name).is_dir():
                    idx += 1
                    name = '{name}_{idx}'.format(name=filename.stem, idx=idx)
            else:
                name = project_name

            Path(project['path']).rename(self.__project_dir/name)
            project['name'] = name
            self.__projects[name] = project
            status = 2

        shutil.rmtree(str(tmp_dir))
        return status

    @login_required
    async def get_client_project(self, request: web.Request):
        uuid = request.match_info['uuid']
        if uuid not in self.__client_projects:
            return jsonp_response(request, {
                'status': 400,
                'msg': 'uuid "{uuid}" not found'.format(uuid=uuid)
            })
        projects = list(self.__client_projects.values())
        return jsonp_response(request, {
            'total': len(projects),
            'rows': projects
        })

    @login_required
    async def get_task(self, request: web.Request):
        page_number = int(request.query.get('pageNumber', '1'))
        page_size = int(request.query.get('pageSize', '5'))

        total = self.__tasks.count()
        rows = [{
            'uuid': row.uuid,
            'session_id': row.session_id,
            'spider_name': row.spider_name,
            'start_time': row.start_time,
            'finish_time': row.finish_time,
            'finish_reason': row.finish_reason
        } for row in self.__tasks.paginate(page_number, page_size)]

        return jsonp_response(request, {
            'total': total,
            'rows': rows
        })

    @login_required
    async def get_info(self, request: web.Request):
        return jsonp_response(request, {
            'status': 0,
            'connection_count': self.__unverified_clients.count(),
            'crawler_count': self.__verified_clients.count(),
            'project_count': len(self.__projects),
            'task_count': 0
        })

    @login_required
    async def get_header(self, request: web.Request):
        session = await get_session(request)
        header = aiohttp_jinja2.render_template('header.html', request, {
            'username': session['username'],
            'connection_count': self.__unverified_clients.count(),
            'crawler_count': self.__verified_clients.count(),
            'project_count': len(self.__projects),
            'task_count': 0
        }).body.decode()
        return jsonp_response(request, {
            'status': 0,
            'header': header
        })

    @login_required
    async def edit(self, request: web.Request):
        return aiohttp_jinja2.render_template('edit.html', request, {})

    @login_required
    async def put_into_blacklist(self, request: web.Request):
        remote_host = request.match_info['remote']

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
        remote_ip = request.match_info['remote']
        if remote_ip in self.__blacklist:
            self.__blacklist.pop(remote_ip)
            return jsonp_response(request, {
                'status': 0,
            })
        else:
            return jsonp_response(request, {
                'status': 100,
                'msg': 'remote "{remote}" not found'.format(remote=remote_ip)
            })

    async def get_websocket_token(self, request: web.Request):
        if self.is_ban(request.remote) or not re.match(self.__ip_pattern, request.match_info['host']):
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

    async def receive(self, websocket: web.WebSocketResponse, uuid: str):
        async for msg in websocket:
            # noinspection PyBroadException
            try:
                data = loads(msg.data)
                logger.debug('from {uuid}: {data}'.format(uuid=uuid, data=data))

                if data['classname'] == 'collector':
                    # await self.__job_scheduler.spawn(self.__handle_client_collector(data))
                    pass
                elif data['classname'] == 'client':
                    await self.__job_scheduler.spawn(self.__handler_client(data, uuid))
                    # await self.__job_scheduler.spawn(self.__handle_websocket_client(data))
                elif data['classname'] == 'Monitor':
                    await self.__job_scheduler.spawn(self.__handle_monitor(data))
            except Exception:
                pass

    async def __handler_client(self, data: dict, uuid: str):
        if data['info']['command'] == 1:
            pass
        elif data['info']['command'] == 6:
            self.__client_projects[uuid] = data['info']['projects']
    #
    # async def __handle_client_collector(self, data: dict, uuid: str):
    #     if data['uuid'] not in self.__tasks or data['session_id'] not in self.__tasks[data['uuid']]:
    #         self.__tasks[data['uuid']] = {data['session_id']: {}}
    #     for key, value in data['info'].items():
    #         if key in self.__collector_keys:
    #             self.__tasks[data['uuid']][data['session_id']][key] = value

    async def insert(self):
        while True:
            for uuid, task in self.__tasks.items():
                for session_id, items in task.items():
                    self.task_db.replace(uuid, session_id, items)
            self.__tasks = {}
            await asyncio.sleep(self.__interval)

    # async def __handle_websocket_client(self, data: dict):
    #     if data['info']['command'] == 1:
    #         pass

    async def __handle_monitor(self, data: dict):
        pass

    async def get_crawler_list(self):
        crawler_list = self.client_db.get_verified_client()
        return crawler_list

    async def send_command(self, uuid: str, command: int, info: dict):
        await self.ws_client[uuid]['main'].send_str(dumps({
            'command': command,
            'info': info
        }))
