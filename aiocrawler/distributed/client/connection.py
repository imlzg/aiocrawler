# coding: utf-8
import os
from configparser import ConfigParser
from yarl import URL
from typing import Union
from hashlib import sha1
from pathlib import Path
from ujson import loads, dumps
from time import time
from asyncio import sleep
from loguru import logger
from socket import gethostname, gethostbyname
from aiohttp.client_exceptions import ClientConnectionError, WSServerHandshakeError
from aiohttp import CookieJar
from aiohttp import ClientSession


class WebsocketConnection(object):
    def __init__(self, server_host: str, port: int = 8989):
        self.server_host = server_host
        self.port = port

        self._client_session: ClientSession = None
        self._wait_timeout = 15
        self._total = 24 * 60 * 60
        self.websocket = None
        self.uuid: str = None

        self.__connection_ini = Path('conf') / 'connection.ini'
        self.__connection_ini.parent.mkdir(exist_ok=True)

        self.__config_parser = ConfigParser()
        self.connected = False

    async def _build_client_session(self, url: Union[str, URL]):
        ck = CookieJar(unsafe=True)
        ck.filter_cookies(url)
        self._client_session = ClientSession(cookie_jar=ck)

    async def close(self):
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        if self._client_session and not self._client_session.closed:
            await self._client_session.close()
        self.connected = False

    @staticmethod
    def _get_host_and_hostname():
        hostname = gethostname()
        host = gethostbyname(hostname)
        return host, hostname

    async def _get_connection(self, server_host: str, port: int):
        """
        Waiting for verified and getting connection information
        :param server_host: server host
        :param port: server port
        :return: connection information
        """
        start = time()
        host, hostname = self._get_host_and_hostname()
        url = 'http://{server_host}:{port}/api/server/get_connection_info/host/{host}/hostname/{hostname}'.format(
            server_host=server_host,
            port=port,
            host=host,
            hostname=hostname
        )
        logger.info(url)
        if not self._client_session:
            await self._build_client_session(url)
        while True:
            try:
                async with self._client_session.get(url) as resp:
                    if resp.status != 200:
                        break
                    # noinspection PyBroadException
                    try:
                        data = loads(await resp.text())
                    except Exception:
                        break
                    else:
                        status = data.get('status', None)
                        if status == 0:
                            return data['uuid'], data['token']
                        elif status == 1:
                            break
                        else:
                            logger.debug(data['msg'])
                            await sleep(self._wait_timeout)
            except ClientConnectionError:
                break

            if time() - start >= self._total:
                break
        return {}

    async def connect(self):
        """
        Connect to websocket server
        :return: WebSocketResponse
        """
        logger.debug('Connecting to {server_host}:{port}', server_host=self.server_host, port=self.port)

        data = self._load_connection_from_environ() or self._load_connection_from_ini() or await self._get_connection(
            server_host=self.server_host, port=self.port)

        if data:
            uuid, token = data
            self._set_connection_to_environ(uuid, token)
            self._set_connection_to_ini(uuid, token)

            self.uuid = uuid
            self.connected = True

            self.websocket = await self._connect(self.server_host, self.port, uuid, token)
            logger.success('Connected to {server_host}:{port}', server_host=self.server_host, port=self.port)
        else:
            logger.error('Cannot connect to {server_host}:{port}', server_host=self.server_host, port=self.port)

    async def _connect(self, host: str, port: int, uuid: str, token: str):
        ws_url = 'ws://{host}:{port}/api/server/connect/uuid/{uuid}/token/{token}'.format(
            host=host,
            port=port,
            uuid=uuid,
            token=token,
        )
        try:
            websocket = await self._client_session.ws_connect(ws_url, timeout=30)
        except (ClientConnectionError, WSServerHandshakeError):
            return None
        else:
            return websocket

    @staticmethod
    def _load_connection_from_environ():
        uuid = os.environ.get('AIOCRAWLER_CLIENT_UUID', None)
        token = os.environ.get('AIOCRAWLER_CLIENT_TOKEN', None)
        if uuid and token:
            return uuid, token

    @staticmethod
    def _set_connection_to_environ(uuid: str, token: str):
        os.environ['AIOCRAWLER_CLIENT_UUID'] = uuid
        os.environ['AIOCRAWLER_CLIENT_TOKEN'] = token

    def _load_connection_from_ini(self):
        uuid = self.__config_parser.get('connection', 'uuid', fallback=None)
        token = self.__config_parser.get('connection', 'token', fallback=None)
        if uuid and token:
            return uuid, token

    def _set_connection_to_ini(self, uuid: str, token: str):
        if not self.__config_parser.has_section('connection'):
            self.__config_parser.add_section('connection')
        self.__config_parser.set('connection', 'uuid', uuid)
        self.__config_parser.set('connection', 'token', token)
        with self.__connection_ini.open('w') as f:
            self.__config_parser.write(f)

    async def send_json(self, info, classname: str = None):
        data = {
            'classname': classname,
            'info': info
        }
        await self.websocket.send_str(dumps(data))
