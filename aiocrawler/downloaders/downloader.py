# coding: utf-8
from typing import Union
from parsel import Selector
from ujson import loads
from aiocrawler import Request
from aiocrawler import Response
from aiocrawler import BaseSettings, logger


class BaseDownloader(object):
    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.logger = logger

    async def download(self, request: Request) -> Union[Response, Exception, None]:
        raise NotImplementedError('{} get_response is not define'.format(self.__class__.__name__))

    def __parse_html__(self, request: Request, response: Response) -> Response:
        if request.handle_way == 'json':
            try:
                response.json = loads(response.text)
            except Exception as e:
                self.logger.error(e)
        elif request.handle_way == 'selector':
            response.selector = Selector(text=response.text)
        return response
