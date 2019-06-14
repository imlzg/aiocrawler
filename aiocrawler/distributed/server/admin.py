# coding: utf-8
import asyncio
import aiohttp_jinja2
import aiojobs
from typing import List, Dict
from ujson import dumps
from aiohttp import web
from aiohttp_session import get_session
from aiocrawler.distributed.server.model.user_model import UserDatabase
from aiocrawler.distributed.server.utils import (jsonp_response,
                                                 login_required,
                                                 PERMISSIONS,
                                                 gen_token)


class Admin(object):
    def __init__(self, job_scheduler: aiojobs.Scheduler = None):
        self._user_db = UserDatabase()
        self._rsa_pub: str = None

        self._token = {}    # {remote: token}
        self._websocket: Dict[str, web.WebSocketResponse] = {}    # {token: websocket}
        self.__interval = 2
        self.__scheduler = job_scheduler

        self.messages: List[dict] = []

    def routes(self):
        return [
            web.get('/user/register', self.register, name='register'),
            web.post('/api/user/register', self.register, name='register_api'),

            web.get('/user/login', self.login, name='login'),
            web.post('/api/user/login', self.login, name='login_api'),

            web.get('/api/user/nav', self.get_nav_api, name='nav_api'),
            web.get('/user/logout', self.logout, name='user-logout'),

            web.get(r'/api/user/websocket/{token}', self.websocket, name='user_websocket'),

        ]

    async def register(self, request: web.Request):
        if self._user_db.is_user_exists():
            return jsonp_response(request, {
                'status': 100,
                'msg': 'This method does not allow to visit after initialization'
            })
        if request.method == 'GET':
            return aiohttp_jinja2.render_template('register.html', request, {})
        elif request.method == 'POST':
            form_data = await request.post()
            if 'username' in form_data and 'password' in form_data:
                self._user_db.create_user(form_data['username'], form_data['password'], permission=0)
                if self._user_db.is_user_exists():
                    await self.authorize_user(request, form_data['username'])

                    return jsonp_response(request, {
                        'status': 0,
                        'msg': 'success',
                        'url': str(request.app.router['index'].url_for())
                    })

        return jsonp_response(request, {
            'status': 101,
            'msg': 'Something went wrong'
        })

    async def authorize_user(self, request: web.Request, username: str):
        session = await get_session(request)
        session['username'] = username
        session['token'] = gen_token()
        self._token[request.remote] = session['token']

    async def login(self, request: web.Request):
        if not self._user_db.is_user_exists():
            return web.HTTPFound(request.app.router['register'].url_for())

        if request.method == 'GET':
            session = await get_session(request)
            if 'username' in session:
                return web.HTTPFound(request.app.router['index'].url_for())

            return aiohttp_jinja2.render_template('login.html', request, {})

        elif request.method == 'POST':
            form_data = await request.post()
            if 'username' in form_data and 'password' in form_data:
                if self._user_db.has_user(form_data['username'], form_data['password']):
                    await self.authorize_user(request, form_data['username'])

                    return jsonp_response(request, {
                        'status': 0,
                        'msg': 'success',
                        'url': str(request.app.router['index'].url_for())
                    })

            return jsonp_response(request, {
                'status': 200,
                'msg': 'Username or password error'
            })

    @login_required
    async def get_nav_api(self, request: web.Request):
        session = await get_session(request)
        user = self._user_db.get_user_info(session['username'])
        if user:
            resp = {
                'status': 0,
                'data': {
                    'username': user.username,
                    'created_at': user.created_at,
                    'permission': PERMISSIONS[user.permission],
                    'websocket_url': str(request.app.router['user_websocket'].url_for(token=session['token']))
                }
            }
        else:
            resp = {
                'status': 100,
                'msg': 'username: {username} is not found'.format(username=session['username'])
            }
        return jsonp_response(request, resp)

    @login_required
    async def logout(self, request: web.Request):
        session = await get_session(request)
        session.pop('username')
        self._websocket.pop(session['token'], None)
        self._token.pop(request.remote, None)
        session.pop('token', None)
        url = request.app.router['login'].url_for()
        return web.HTTPFound(url)

    async def websocket(self, request: web.Request):
        token = request.match_info.get('token', None)
        if token and self._token.get(request.remote, None) == token:
            websocket = web.WebSocketResponse()
            await websocket.prepare(request)
            self._websocket[token] = websocket

            async for _ in websocket:
                pass
            self._websocket.pop(token, None)
            if not websocket.closed:
                await websocket.close()
            return websocket
        else:
            return web.HTTPNotFound()

    async def __message_loop(self):
        while True:
            if len(self.messages) and len(self._websocket):
                tasks = [
                    asyncio.ensure_future(websocket.send_str(dumps({'message': message})))
                    for message in self.messages
                    for websocket in self._websocket.values()
                ]
                self.messages = []
                await asyncio.wait(tasks)
            await asyncio.sleep(self.__interval)

    async def on_startup(self, _):
        await self.__scheduler.spawn(self.__message_loop())

    async def on_cleanup(self, _):
        for websocket in self._websocket.values():
            if not websocket.closed:
                await websocket.close()

    @staticmethod
    async def _send_json(obj: object, websocket: web.WebSocketResponse):
        if not websocket.closed:
            await websocket.send_str(dumps(obj))

    @login_required
    async def spider_on_server(self, request: web.Request):
        return jsonp_response(request, scan_spider())
