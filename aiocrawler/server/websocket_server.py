# coding: utf-8
from aiohttp import web
from aiocrawler.server.utils import login_required, json_or_jsonp_response, gen_uuid
from aiocrawler.server.model.client_model import ClientDatabase


class WebsocketServer(object):
    def __init__(self):
        self._db = ClientDatabase()
        self.ws_client = {}

    def routes(self):
        return [
            web.get('/api/server/verify', self.verify_api, name='verify'),
            web.get('/api/server/unverified', self.unverified_api, name='unverified'),

            web.get('/api/server/connect', self.handler, name='connect'),

            web.post('/api/server/get_connect_info', self.get_websocket_token, name='get_connect_info'),

            web.get('/api/server/get_verified', self.get_verified_client_api, name='get_verified'),
            web.get('/api/server/get_unverified', self.get_unverified_client_api, name='get_unverified')

        ]

    async def get_websocket_token(self, request: web.Request):
        data = await request.post()
        if 'host' in data and 'hostname' in data and request.remote:
            uuid = gen_uuid(request.remote, data['host'], data['hostname'])
            info = self._db.get_client_info(uuid)
            if info:
                if info.token:
                    return json_or_jsonp_response(request, {
                        'status': 0,
                        'uuid': uuid,
                        'token': info.token
                    })

            else:
                self._db.create_client(request.remote, data['host'], data['hostname'])

        return json_or_jsonp_response(request, {
            'status': 1001,
            'msg': 'Waiting for verification...'
        })

    async def handler(self, request: web.Request):
        uuid = request.match_info.get('uuid', None)
        token = request.match_info.get('token', None)
        if self._db.verify(uuid, token):
            ws = web.WebSocketResponse()
            check = ws.can_prepare(request)
            if check:
                await ws.prepare(request)
                if uuid in self.ws_client:
                    self.ws_client[uuid].append(ws)
                else:
                    self.ws_client[uuid] = [ws]
                return ws

        else:
            return web.Response(text='failed')

    async def close_ws_client(self, _):
        for ws_list in self.ws_client.values():
            for ws in ws_list:
                if not ws.closed:
                    await ws.close()

    @login_required
    async def verify_api(self, request: web.Request):
        uuid = request.match_info.get('uuid', None)
        token = self._db.set_token(uuid)
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
        check = self._db.clear_token(uuid)
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
        client_list = self._db.get_unverified_client()
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
        client_list = self._db.get_verified_client()
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
