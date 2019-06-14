# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin
# PROJECT   : credit
# File      : aio_downloader
import traceback
import asyncio
import requests

from typing import Union
from yarl import URL
from concurrent.futures import ThreadPoolExecutor
from aiocrawler import Response
from aiohttp import ClientSession, CookieJar
from aiocrawler import BaseSettings, Request
from aiohttp_socks import SocksConnector
from aiocrawler.downloaders.downloader import BaseDownloader


class AioDownloader(BaseDownloader):
    def __init__(self, settings: BaseSettings, client_session: ClientSession):
        BaseDownloader.__init__(self, settings)
        self._default_session: ClientSession = client_session

        self._requests_session: requests.Session = None
        self._executor: ThreadPoolExecutor = None
        self._loop: asyncio.AbstractEventLoop = None

    async def download(self, request: Request) -> Union[Response, Exception]:
        session = self._default_session
        new_session = False
        proxy = None

        if request.proxy:
            proxy_url = URL(request.proxy)
            if proxy_url.scheme in ('sock4', 'sock5'):
                connector = SocksConnector.from_url(request.url)
                session = ClientSession(cookie_jar=CookieJar(unsafe=True), connector=connector)
                new_session = True
            elif proxy_url.scheme == 'https' and URL(request.url).scheme == 'https':
                return await self.download_by_requests(request)
            else:
                proxy = request.proxy

        try:
            if request.cookies:
                session.cookie_jar.update_cookies(request.cookies)

            resp = await session.request(method=request.method,
                                         url=request.url,
                                         params=request.params,
                                         data=request.data,
                                         proxy=proxy,
                                         headers=request.headers,
                                         timeout=request.timeout)

            status = resp.status
            text = await resp.text(encoding=request.encoding)
            cookies = resp.cookies

            response = Response(text=text, status=status, cookies=cookies)
            if request.cookies:
                response.cookies.update(request.cookies)

            return response

        except Exception as e:
            self.logger.error(traceback.format_exc(limit=10))
            return e

        finally:
            if new_session:
                await session.close()

    async def download_by_requests(self, request: Request):
        if self._requests_session is None:
            self._requests_session = requests.session()
            max_workers = self.settings.CONCURRENT_REQUESTS if self.settings.CONCURRENT_REQUESTS < 32 else 32
            self._executor = ThreadPoolExecutor(max_workers=max_workers)
            self._loop = asyncio.get_event_loop()

        return await self._loop.run_in_executor(self._executor, self._download_by_requests, request)

    def _download_by_requests(self, request: Request):
        try:
            response = self._requests_session.request(method=request.method,
                                                      url=request.url,
                                                      params=request.params,
                                                      data=request.data,
                                                      headers=request.headers,
                                                      cookies=request.cookies,
                                                      proxies={'https': request.proxy},
                                                      timeout=request.timeout)
            status = response.status_code
            response.encoding = request.encoding
            text = response.text
            response = Response(text=text, status=status, cookies=response.cookies)
            if request.cookies:
                response.cookies.update(request.cookies)

            return response

        except Exception as e:
            self.logger.error(traceback.format_exc(limit=10))
            return e
