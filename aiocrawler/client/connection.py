# coding: utf-8
import os
from yarl import URL
from typing import Union
from ujson import loads
from time import time
from asyncio import sleep
from loguru import logger
from socket import gethostname, gethostbyname
from aiohttp.client_exceptions import ClientConnectionError, WSServerHandshakeError
from aiohttp import CookieJar
from aiohttp import ClientSession


class WebsocketConnection(object):
    def __init__(self):
        self._client_session: ClientSession = None
        self._wait_timeout = 15
        self._total = 24 * 60 * 60
        self._ws = None
        self.uuid: str = None

    async def _build_client_session(self, url: Union[str, URL]):
        ck = CookieJar(unsafe=True)
        ck.filter_cookies(url)
        self._client_session = ClientSession(cookie_jar=ck)

    async def close(self):
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._client_session and not self._client_session.closed:
            await self._client_session.close()

    @staticmethod
    def _get_host_and_hostname():
        hostname = gethostname()
        host = gethostbyname(hostname)
        return host, hostname

    async def _get_connection_info(self, ip: str, port: int):
        """
        Waiting for verified and getting connection information
        :param ip: server ip
        :param port: server port
        :return: connection information
        """
        start = time()
        token_url = 'http://{ip}:{port}/api/server/get_connect_info'.format(ip=ip, port=port)
        host, hostname = self._get_host_and_hostname()
        post_data = {
            'host': host,
            'hostname': hostname
        }

        if not self._client_session:
            await self._build_client_session(token_url)
        while True:
            try:
                data = {}
                async with self._client_session.post(token_url, json=post_data) as resp:
                    if resp.status != 200:
                        break
                    try:
                        data = loads(await resp.text())
                    finally:
                        if data.get('status', 1) == 0:
                            return data
                        else:
                            logger.debug(data['msg'])
                            await sleep(self._wait_timeout)
            except ClientConnectionError:
                break

            if time() - start >= self._total:
                break

    async def connect(self, ip: str, port: int):
        """
        Connect to websocket server
        :param ip: server ip
        :param port: server port
        :return: WebSocketResponse
        """
        logger.debug('Connecting to {ip}:{port}', ip=ip, port=port)

        uuid = os.environ.get('AIOCRAWLER_CLIENT_UUID', None)
        token = os.environ.get('AIOCRAWLER_CLIENT_TOKEN', None)

        if not uuid or not token:
            data = await self._get_connection_info(ip, port)
            if data:
                uuid = data.get('uuid', None)
                token = data.get('token', None)
                os.environ['AIOCRAWLER_CLIENT_UUID'] = uuid
                os.environ['AIOCRAWLER_CLIENT_TOKEN'] = token
                self.uuid = uuid

        if uuid and token:
                return await self._connect(ip, port, uuid, token)

        logger.error('Cannot connect to {ip}:{port}', ip=ip, port=port)

    async def _connect(self, ip: str, port: int, uuid: str, token: str):
        ws_url = 'ws://{ip}:{port}/api/server/connect?uuid={uuid}&token={token}'.format(
            ip=ip,
            port=port,
            uuid=uuid,
            token=token
        )
        try:
            ws = await self._client_session.ws_connect(ws_url)
        except (ClientConnectionError, WSServerHandshakeError):
            return None
        else:
            return ws
