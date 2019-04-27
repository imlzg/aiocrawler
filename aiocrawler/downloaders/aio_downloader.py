# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin
# PROJECT   : credit
# File      : aio_downloader
import traceback
from aiohttp import ClientSession
from aiocrawler.response import Response
from aiocrawler.downloaders.downloader import BaseDownloader
from aiocrawler.settings import BaseSettings


class AioDownloader(BaseDownloader):
    def __init__(self, settings: BaseSettings):
        BaseDownloader.__init__(self, settings)

    async def get_response(self, request):
        session = ClientSession()
        try:
            if request['cookies']:
                session.cookie_jar.update_cookies(request['cookies'])

            if request['method'] == 'GET':
                resp = await session.get(request['url'],
                                         params=request['params'],
                                         proxy=request['proxy'],
                                         headers=request['headers'],
                                         timeout=request['timeout'],
                                         )
            else:
                resp = await session.post(url=request['url'],
                                          data=request['params'],
                                          proxy=request['proxy'],
                                          headers=request['headers'],
                                          timeout=request['timeout'],
                                          )

            status = resp.status
            text = await resp.text(encoding=request['encoding'])
            cookies = resp.cookies

            response = Response(text=text, status=status, cookies=cookies)
            if request['cookies']:
                response.cookies.update(request['cookies'])

            return response

        except Exception as e:
            self.logger.error(traceback.format_exc(limit=10))
            return e

        finally:
            await session.close()

