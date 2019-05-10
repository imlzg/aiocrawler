import asyncio
import datetime
import logging
import os
import socket
import sys
from base64 import urlsafe_b64decode
from json import dumps
from math import ceil
from random import randint
from ssl import SSLContext
from typing import (
    Awaitable, Callable, Iterable, List, Optional, Tuple, Type, Union, cast)

import aiohttp_jinja2
import aiohttp_session
from aiocrawler import BaseSettings
from aiohttp import web
from aiohttp.abc import AbstractAccessLogger
from aiohttp.log import access_logger
from aiohttp.web import Application
from aiohttp.web_log import AccessLogger
from aiohttp.web_request import Request
from aiohttp.web_runner import AppRunner, BaseSite, SockSite, TCPSite, UnixSite
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
        self.__seconds = 1 * 60 * 60  # 1 hour(s)
        self.__interval = 5  # s
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
            self.generate_data(now - datetime.timedelta(seconds=i * self.__interval), 0) for i in range(num)
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

    @staticmethod
    async def run_app(app: Union[Application, Awaitable[Application]], *,
                        host: Optional[str] = None,
                        port: Optional[int] = None,
                        path: Optional[str] = None,
                        sock: Optional[socket.socket] = None,
                        shutdown_timeout: float = 60.0,
                        ssl_context: Optional[SSLContext] = None,
                        print_: Callable[..., None] = print,
                        backlog: int = 128,
                        access_log_class: Type[AbstractAccessLogger] = AccessLogger,
                        access_log_format: str = AccessLogger.LOG_FORMAT,
                        access_log: Optional[logging.Logger] = access_logger,
                        handle_signals: bool = True,
                        reuse_address: Optional[bool] = None,
                        reuse_port: Optional[bool] = None) -> None:
        # A internal functio to actually do all dirty job for application running
        if asyncio.iscoroutine(app):
            app = await app  # type: ignore

        app = cast(Application, app)

        runner = AppRunner(app, handle_signals=handle_signals,
                           access_log_class=access_log_class,
                           access_log_format=access_log_format,
                           access_log=access_log)

        await runner.setup()

        sites = []  # type: List[BaseSite]

        try:
            if host is not None:
                if isinstance(host, (str, bytes, bytearray, memoryview)):
                    sites.append(TCPSite(runner, host, port,
                                         shutdown_timeout=shutdown_timeout,
                                         ssl_context=ssl_context,
                                         backlog=backlog,
                                         reuse_address=reuse_address,
                                         reuse_port=reuse_port))
                else:
                    for h in host:
                        sites.append(TCPSite(runner, h, port,
                                             shutdown_timeout=shutdown_timeout,
                                             ssl_context=ssl_context,
                                             backlog=backlog,
                                             reuse_address=reuse_address,
                                             reuse_port=reuse_port))
            elif path is None and sock is None or port is not None:
                sites.append(TCPSite(runner, port=port,
                                     shutdown_timeout=shutdown_timeout,
                                     ssl_context=ssl_context, backlog=backlog,
                                     reuse_address=reuse_address,
                                     reuse_port=reuse_port))

            if path is not None:
                if isinstance(path, (str, bytes, bytearray, memoryview)):
                    sites.append(UnixSite(runner, path,
                                          shutdown_timeout=shutdown_timeout,
                                          ssl_context=ssl_context,
                                          backlog=backlog))
                else:
                    for p in path:
                        sites.append(UnixSite(runner, p,
                                              shutdown_timeout=shutdown_timeout,
                                              ssl_context=ssl_context,
                                              backlog=backlog))

            if sock is not None:
                if not isinstance(sock, Iterable):
                    sites.append(SockSite(runner, sock,
                                          shutdown_timeout=shutdown_timeout,
                                          ssl_context=ssl_context,
                                          backlog=backlog))
                else:
                    for s in sock:
                        sites.append(SockSite(runner, s,
                                              shutdown_timeout=shutdown_timeout,
                                              ssl_context=ssl_context,
                                              backlog=backlog))
            for site in sites:
                await site.start()

            if print_:  # pragma: no branch
                names = sorted(str(s.name) for s in runner.sites)
                print_("======== Running on {} ========\n"
                       "(Press CTRL+C to quit)".format(', '.join(names)))
            while True:
                await asyncio.sleep(3600)  # sleep forever by 1 hour intervals
        finally:
            await runner.cleanup()

    @staticmethod
    def cancel_all_tasks(loop: asyncio.AbstractEventLoop) -> None:
        to_cancel = asyncio.Task.all_tasks(loop)
        if not to_cancel:
            return

        for task in to_cancel:
            task.cancel()

        loop.run_until_complete(
            asyncio.gather(*to_cancel, loop=loop, return_exceptions=True))

        for task in to_cancel:
            if task.cancelled():
                continue
            if task.exception() is not None:
                loop.call_exception_handler({
                    'message': 'unhandled exception during asyncio.run() shutdown',
                    'exception': task.exception(),
                    'task': task,
                })

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
        return app
