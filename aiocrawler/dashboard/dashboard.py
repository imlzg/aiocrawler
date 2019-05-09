import datetime
import os
import sys
import asyncio
from math import ceil
from base64 import urlsafe_b64decode
from json import dumps
from random import randint
from typing import Union, List, Tuple
from aiocrawler import BaseSettings
import aiohttp_jinja2
import aiohttp_session
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp_session import get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
from jinja2 import FileSystemLoader


def login_required(fn):
    async def wrapped(self, request, *args, **kwargs):
        app = request.app
        routers = app.router

        session = await get_session(request)

        if 'username' not in session:
            return web.HTTPFound(routers['login'].url_for())

        return await fn(self, request, *args, **kwargs)

    return wrapped


class Dashboard:
    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.logger = self.settings.LOGGER
        self.__item_at = 0
        self.__seconds = 1 * 60 * 60    # 1 hour(s)
        self.__interval = 5    # s
        self.__item_info: List[Tuple[str, Union[int, float]]] = []

    @aiohttp_jinja2.template("index.html")
    @login_required
    async def index(self, request: Request):
        session = await get_session(request)
        return {
            "username": session["username"]
        }

    async def get_redis_info(self):
        data = {
            'aiocrawler_count': randint(1, 10),
            'download_count': randint(1, 10),
            'request_count': randint(1, 10),
            'item_info': self.__item_info
        }
        return data

    async def login(self, request: Request):
        session = await get_session(request)
        is_login = session['username'] if 'username' in session else None
        if is_login:
            router = request.app.router
            return web.HTTPFound(router['index'].url_for())

        if request.method == 'GET':
            return aiohttp_jinja2.render_template('login.html', request, {
                'type': 'warning',
                'message': 'Sign in to dashboard'})

        elif request.method == 'POST':
            form_data = await request.post()
            username = self.validate_login(form_data)
            if username:
                session['username'] = username
                index_url = request.app.router["index"].url_for()
                return web.HTTPFound(index_url)
            else:
                return aiohttp_jinja2.render_template('login.html', request, {
                    'type': 'danger',
                    'message': 'Username or password error'
                })

    @login_required
    async def logout(self, request):
        session = await get_session(request)
        session.pop('username')
        url = request.app.router['login'].url_for()
        return web.HTTPFound(url)

    @login_required
    async def update_info(self, request: Request):

        data = await self.get_redis_info()
        if '_' in request.query:
            return web.Response(text=self.jsonp(data, request.query.get('callback', 'callback')))
        return web.json_response(data)

    @staticmethod
    def jsonp(data: dict, callback: str):
        text = '{callback}({data})'.format(callback=callback, data=dumps(data))
        return text

    def validate_login(self, form_data):
        admin_user = os.environ.get('DASHBOARD_USER', None) or self.settings.DASHBOARD_USER

        if not admin_user:
            self.logger.warning('DASHBOARD_USER is not configure in the {}'.format(self.settings.__class__.__name__))

        admin_password = os.environ.get('DASHBOARD_PASSWORD', None)
        if admin_user == form_data.get('username') and admin_password == form_data.get('password', None):
            return admin_user
        return None

    async def set_item_count_history(self):
        # initialize item_count_history
        now = datetime.datetime.now()
        num = ceil(self.__seconds / self.__interval)
        self.__item_info = [
            self.generate_data(now - datetime.timedelta(seconds=i*self.__interval), 0) for i in range(num)
        ]

        while True:
            item_count = randint(1, 100)
            now = datetime.datetime.now()
            self.__item_info.pop(0)
            self.__item_info.append(self.generate_data(now, item_count))
            await asyncio.sleep(self.__interval)

    @staticmethod
    def generate_data(now: datetime.datetime, value: Union[int, float]):
        data = {
            'name': now.strftime("%Y-%m-%d %H:%M:%S"),
            'value': [
                now.strftime('%Y-%m-%d %H:%M:%S'),
                value
            ]
        }
        return data

    def run(self):
        current_dir = os.path.dirname(__file__)
        if current_dir not in sys.path:
            sys.path.append(current_dir)

        app = web.Application()
        fernet_key = fernet.Fernet.generate_key()
        secret_key = urlsafe_b64decode(fernet_key)
        aiohttp_session.setup(app, EncryptedCookieStorage(secret_key, cookie_name='aiocrawler_session'))

        aiohttp_jinja2.setup(app, loader=FileSystemLoader('templates'))
        app.add_routes([
            web.get('/login', self.login, name='login'),
            web.post('/login', self.login),
            web.get('/index', self.index, name='index'),
            web.get('/', self.index),
            web.get('/update', self.update_info),
            web.get('/logout', self.logout),

            web.static('/imgs', 'templates/imgs'),
            web.static('/js', 'templates/js'),
            web.static('/css', 'templates/css'),
            web.static('/vendor', 'templates/vendor'),
            web.static('/fonts', 'templates/fonts')
        ])

        loop = asyncio.get_event_loop()
        try:
            asyncio.ensure_future(self.set_item_count_history())
            asyncio.ensure_future(web._run_app(app))
            loop.run_forever()
        finally:
            web._cancel_all_tasks(loop)
            loop.close()
