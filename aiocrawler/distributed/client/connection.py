# coding: utf-8
import os
from yarl import URL
from typing import Union
from hashlib import sha1
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
        self.__server_host = server_host
        self.__port = port

        self._client_session: ClientSession = None
        self._wait_timeout = 15
        self._total = 24 * 60 * 60
        self.websocket = None
        self.uuid: str = None
        self.session_id = sha1(os.urandom(40)).hexdigest()

    async def _build_client_session(self, url: Union[str, URL]):
        ck = CookieJar(unsafe=True)
        ck.filter_cookies(url)
        self._client_session = ClientSession(cookie_jar=ck)

    async def close(self):
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        if self._client_session and not self._client_session.closed:
            await self._client_session.close()

    @staticmethod
    def _get_host_and_hostname():
        hostname = gethostname()
        host = gethostbyname(hostname)
        return host, hostname

    async def _get_connection_info(self, server_host: str, port: int):
        """
        Waiting for verified and getting connection information
        :param server_host: server host
        :param port: server port
        :return: connection information
        """
        start = time()
        host, hostname = self._get_host_and_hostname()
        url = 'http://{server_host}:{port}/api/server/get_connect_info/{host}/{hostname}'.format(
            server_host=server_host,
            port=port,
            host=host,
            hostname=hostname
        )

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
                            return data
                        elif status == 1:
                            break
                        else:
                            logger.debug(data['msg'])
                            await sleep(self._wait_timeout)
            except ClientConnectionError:
                break

            if time() - start >= self._total:
                break

    async def connect(self):
        """
        Connect to websocket server
        :return: WebSocketResponse
        """
        logger.debug('Connecting to {server_host}:{port}', server_host=self.__server_host, port=self.__port)

        uuid = os.environ.get('AIOCRAWLER_CLIENT_UUID', None)
        token = os.environ.get('AIOCRAWLER_CLIENT_TOKEN', None)

        if not uuid or not token:
            data = await self._get_connection_info(self.__server_host, self.__port)
            if data:
                uuid = data.get('uuid', None)
                token = data.get('token', None)
                os.environ['AIOCRAWLER_CLIENT_UUID'] = uuid
                os.environ['AIOCRAWLER_CLIENT_TOKEN'] = token
                self.uuid = uuid

        if uuid and token:
                self.websocket = await self._connect(self.__server_host, self.__port, uuid, token)

        logger.error('Cannot connect to {server_host}:{port}', server_host=self.__server_host, port=self.__port)

    async def _connect(self, server_host: str, port: int, uuid: str, token: str):
        ws_url = 'ws://{server_host}:{port}/api/server/connect/{token}/{uuid}/{session_id}'.format(
            server_host=server_host,
            port=port,
            uuid=uuid,
            token=token,
            session_id=self.session_id
        )
        try:
            websocket = await self._client_session.ws_connect(ws_url)
        except (ClientConnectionError, WSServerHandshakeError):
            return None
        else:
            return websocket

    async def send_json(self, info, classname=None):
        data = {
            'uuid': self.uuid,
            'session_id': self.session_id,
            'classname': classname,
            'info': info
        }
        await self.websocket.send_str(dumps(data))
