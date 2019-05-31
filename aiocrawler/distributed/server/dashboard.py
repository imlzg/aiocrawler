import sys
import aiojobs
from pathlib import Path
from base64 import urlsafe_b64decode
from aiocrawler.distributed.server.admin import Admin
from aiocrawler.distributed.server.server import WebsocketServer
from aiocrawler.distributed.server.utils import login_required

import aiohttp_jinja2
import aiohttp_session
from aiocrawler import logger
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp_session import get_session
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
    def __init__(self):
        self.__job_scheduler: aiojobs.Scheduler = None

    @aiohttp_jinja2.template("index.html")
    @login_required
    async def index(self, request: Request):
        """
        index page
        :param request: web request
        :return:
        """
        session = await get_session(request)
        return {
            "username": session["username"]
        }

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

        server = WebsocketServer(job_scheduler=self.__job_scheduler)
        app.add_routes(server.routes())
        app.on_cleanup.append(server.close_ws_client)

        admin = Admin(server)
        app.add_routes(admin.routes())
        # app.on_startup.append(admin.on_startup)
        app.on_startup.append(self.on_startup)
        app.on_cleanup.append(admin.on_cleanup)

        app.add_routes([
            web.get('/index', self.index, name='index'),
            web.get('/', self.index),
            web.static('/css', 'templates/css'),
            web.static('/fonts', 'templates/fonts'),
            web.static('/img', 'templates/img'),
            web.static('/js', 'templates/js'),
            web.static('/vendor', 'templates/vendor'),
            web.static('/sass', 'templates/sass')
        ])
        return app

    async def on_startup(self, _):
        self.__job_scheduler = await aiojobs.create_scheduler(limit=None)

    def run(self):
        current_dir = str(Path().absolute())
        if current_dir not in sys.path:
            sys.path.append(current_dir)

        app = self.create_app()
        web.run_app(app, host='0.0.0.0', port=8989, print=logger.debug)


if __name__ == '__main__':
    d = Dashboard()
    d.run()
