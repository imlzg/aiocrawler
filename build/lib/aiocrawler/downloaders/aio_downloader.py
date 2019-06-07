# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin
# PROJECT   : credit
# File      : aio_downloader
import traceback
from yarl import URL
from aiocrawler import Response
from aiohttp import ClientSession
from aiocrawler import BaseSettings
from aiohttp_socks import SocksConnector
from aiocrawler.downloaders.downloader import BaseDownloader


class AioDownloader(BaseDownloader):
    def __init__(self, settings: BaseSettings):
        BaseDownloader.__init__(self, settings)

    async def download(self, request):
        connector = None
        proxy = None
        if request.proxy:
            proxy_url = URL(request.proxy)
            if proxy_url.scheme in ['socks4', 'socks5']:
                connector = SocksConnector.from_url(request.proxy)
            else:
                proxy = request.proxy

        session = ClientSession(connector=connector)
        try:
            if request.cookies:
                session.cookie_jar.update_cookies(request.cookies)

            if request.method == 'GET':
                resp = await session.get(request.url,
                                         params=request.params,
                                         proxy=proxy,
                                         headers=request.headers,
                                         timeout=request.timeout,
                                         )
            else:
                resp = await session.post(url=request.url,
                                          data=request.params,
                                          proxy=proxy,
                                          headers=request.headers,
                                          timeout=request.timeout,
                                          )

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
            await session.close()
