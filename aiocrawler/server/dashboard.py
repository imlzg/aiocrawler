import asyncio
import datetime
from base64 import urlsafe_b64decode
from math import ceil
from random import randint
from typing import (List, Tuple, Union)
from sys import path
from pathlib import Path

from aiocrawler.server.user import User
from aiocrawler.server.websocket_server import WebsocketServer
from aiocrawler.server.utils import json_or_jsonp_response, login_required

import aiohttp_jinja2
import aiohttp_session
from aiocrawler import BaseSettings, logger
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp_session import get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
from jinja2 import FileSystemLoader


class Dashboard(object):
    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.__item_at = 0
        self.__seconds = 1 * 60 * 60  # 1 hour(s)
        self.__interval = 5  # s
        self.__item_info: List[Tuple[str, Union[int, float]]] = []

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

    async def get_redis_info(self):
        data = {
            'aiocrawler_count': randint(1, 10),
            'download_count': randint(1, 10),
            'request_count': randint(1, 10),
            'item_info': self.__item_info
        }
        return data

    @login_required
    async def update_info(self, request: Request):

        data = await self.get_redis_info()
        return json_or_jsonp_response(request, data)

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

    def create_app(self) -> web.Application:
        """
        create a web app
        :return: app
        """
        app = web.Application()
        fernet_key = fernet.Fernet.generate_key()
        secret_key = urlsafe_b64decode(fernet_key)
        aiohttp_session.setup(app, EncryptedCookieStorage(secret_key, cookie_name='aiocrawler_session'))

        aiohttp_jinja2.setup(app, loader=FileSystemLoader('aiocrawler/server/templates'))

        user = User(self.settings)
        app.add_routes(user.routes())

        websocket_server = WebsocketServer()
        app.add_routes(websocket_server.routes())

        app.add_routes([
            web.get('/index', self.index, name='index'),
            web.get('/', self.index),
            web.get('/update', self.update_info),
        ])
        return app

    def run(self):
        app = self.create_app()
        web.run_app(app, host='0.0.0.0', port=8080, print=logger.debug)
