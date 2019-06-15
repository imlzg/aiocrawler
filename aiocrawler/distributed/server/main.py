import sys
import asyncio
import aiojobs
from pathlib import Path
from base64 import urlsafe_b64decode
from typing import Union
from aiocrawler.distributed.server.admin import Admin
from aiocrawler.distributed.server.server import WebsocketServer
from aiocrawler.distributed.server.utils import login_required

import aiohttp_jinja2
import aiohttp_session
from aiocrawler import logger
from aiohttp import web
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
from jinja2 import FileSystemLoader


@web.middleware
async def status404(request, handler):
    try:
        response = await handler(request)
        if response.status != 404:
            return response
    except web.HTTPException:
        pass

    return aiohttp_jinja2.render_template('404.html', request, {})


class Dashboard(object):
    def __init__(self, project_dir: Union[str, Path] = None):
        self.__job_scheduler: aiojobs.Scheduler = aiojobs.Scheduler(close_timeout=0.1,
                                                                    limit=None,
                                                                    pending_limit=10000,
                                                                    exception_handler=None,
                                                                    loop=asyncio.get_event_loop())
        self._project_dir = Path(project_dir) if project_dir else Path()

    @login_required
    async def index(self, request: web.Request):
        return aiohttp_jinja2.render_template('index.html', request, {})

    @login_required
    async def connection(self, request: web.Request):
        return aiohttp_jinja2.render_template('connection.html', request, {})

    @login_required
    async def crawler(self, request: web.Request):
        return aiohttp_jinja2.render_template('crawler.html', request, {})

    @login_required
    async def project(self, request: web.Request):
        return aiohttp_jinja2.render_template('project.html', request, {})

    @login_required
    async def task(self, request: web.Request):
        return aiohttp_jinja2.render_template('task.html', request, {})

    @login_required
    async def get_header(self, request: web.Request):
        return aiohttp_jinja2.render_template('header.html', request, {})

    def create_app(self) -> web.Application:
        """
        create a web app
        :return: app
        """
        app = web.Application(middlewares=[status404, ])
        fernet_key = fernet.Fernet.generate_key()
        secret_key = urlsafe_b64decode(fernet_key)
        aiohttp_session.setup(app, EncryptedCookieStorage(secret_key, cookie_name='aiocrawler_session'))

        aiohttp_jinja2.setup(app, loader=FileSystemLoader('templates'))

        admin = Admin(job_scheduler=self.__job_scheduler)
        app.add_routes(admin.routes())
        app.on_startup.append(admin.on_startup)
        app.on_cleanup.append(admin.on_cleanup)

        server = WebsocketServer(job_scheduler=self.__job_scheduler, admin=admin, project_dir=self._project_dir)
        app.add_routes(server.routes())
        app.on_cleanup.append(server.close_ws_client)

        app.add_routes([
            web.get('/index', self.index, name='index'),
            web.get('/connection', self.connection, name='connection'),
            web.get('/crawler', self.crawler, name='crawler'),
            web.get('/project', self.project, name='project'),
            web.get('/task', self.task, name='task'),

            web.get('/', self.index),
            web.static('/css', 'templates/css'),
            web.static('/fonts', 'templates/fonts'),
            web.static('/img', 'templates/img'),
            web.static('/js', 'templates/js'),
            web.static('/vendor', 'templates/vendor'),
            web.static('/sass', 'templates/sass')
        ])
        return app

    def run(self):
        app = self.create_app()
        web.run_app(app, host='0.0.0.0', port=8989, print=logger.debug)


if __name__ == '__main__':
    current_dir = str(Path().absolute())
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    d = Dashboard(project_dir='demo')
    d.run()
