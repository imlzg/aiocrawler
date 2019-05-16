# coding: utf-8
import aiohttp_jinja2
from aiocrawler import BaseSettings
from aiohttp import web
from aiocrawler.server.utils import json_or_jsonp_response, login_required, PERMISSIONS
from aiohttp_session import get_session
from cryptography.fernet import Fernet
from aiocrawler.server.model.user_model import UserDatabase, RsaDatabase


class User(object):
    def __init__(self, settings: BaseSettings):
        self._settings = settings
        self._logger = self._settings.LOGGER
        self._user_db = UserDatabase()
        self._rsa_db = RsaDatabase()
        self._rsa_pub: str = None

    def routes(self):
        return [
            web.get('/user/register', self.register, name='register'),
            web.post('/api/user/register', self.register, name='register_api'),

            web.get('/user/login', self.login, name='login'),
            web.post('/api/user/login', self.login, name='login_api'),

            web.get('/api/user/nav', self.get_nav_api, name='nav_api'),

            web.get('/user/logout', self.logout, name='logout'),

            web.get('/api/user/pub', self.get_public_key, name='pub'),

            web.static('/user/css', 'aiocrawler/server/templates/css'),
            web.static('/user/fonts', 'aiocrawler/server/templates/fonts'),
            web.static('/user/imgs', 'aiocrawler/server/templates/imgs'),
            web.static('/user/js', 'aiocrawler/server/templates/js'),
            web.static('/user/vendor', 'aiocrawler/server/templates/vendor')
        ]

    async def register(self, request: web.Request):
        if self._user_db.is_user_exists():
            return json_or_jsonp_response(request, {
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
                    session = await get_session(request)
                    session['username'] = form_data['username']
                    return json_or_jsonp_response(request, {
                        'status': 0,
                        'msg': 'success',
                        'url': str(request.app.router['index'].url_for())
                    })

        return json_or_jsonp_response(request, {
            'status': 101,
            'msg': 'Something went wrong'
        })

    async def get_public_key(self, request: web.Request):
        if not self._rsa_pub:
            self._rsa_pub = self._rsa_db.get_public_key()
        return json_or_jsonp_response(request, {
            'status': 0,
            'pub': self._rsa_pub
        })

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
                    session = await get_session(request)
                    session['username'] = form_data['username']
                    return json_or_jsonp_response(request, {
                        'status': 0,
                        'msg': 'success',
                        'url': str(request.app.router['index'].url_for())
                    })

            return json_or_jsonp_response(request, {
                'status': 200,
                'msg': 'Username or password error'
            })

    @login_required
    async def get_nav_api(self, request: web.Request):
        session = await get_session(request)
        if 'token' not in session:
            token = Fernet.generate_key().decode()
            session['token'] = token
        user = self._user_db.get_user_info(session['username'])
        if user:
            resp = {
                'status': 0,
                'data': {
                    'username': user.username,
                    'created_at': user.created_at,
                    'permission': PERMISSIONS[user.permission],
                    'token': session['token']
                }
            }
        else:
            resp = {
                'status': 100,
                'msg': '{username} is not in db'.format(username=session['username'])
            }
        return json_or_jsonp_response(request, resp)

    @login_required
    async def logout(self, request: web.Request):
        session = await get_session(request)
        session.pop('username')
        session.pop('token', None)
        url = request.app.router['login'].url_for()
        return web.HTTPFound(url)
