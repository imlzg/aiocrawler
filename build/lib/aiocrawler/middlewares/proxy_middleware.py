# coding: utf-8
from aiocrawler import BaseSettings
from aiocrawler import Request
from aiocrawler import Response
from aiocrawler.middlewares.middleware import BaseMiddleware


class AioProxyMiddleware(BaseMiddleware):

    async def process_request(self, request: Request):
        pass

    async def process_response(self, request: Request, response: Response):
        pass

    async def process_exception(self, request: Request, exception: Exception):
        pass
