# coding: utf-8
from json import loads
from parsel import Selector
from typing import Union, List
from aiocrawler.request import Request
from aiocrawler.response import Response
from aiocrawler.settings import BaseSettings


class Spider(object):
    name: str = None
    words: List[str] = None

    def __init__(self, settings: BaseSettings):
        self.setting = settings
        self.logger = self.setting.LOGGER

    def make_request(self, word: str) -> Union[List[Request], Request]:
        raise NotImplementedError('{} make_request method is not define'.format(self.__class__.__name__))

    def parse(self, response: Response):
        pass

    def __handle__(self, request: Request, response: Response) -> Response:
        if request['handle_way'] == 'json':
            try:
                response.json = loads(response.text)
            except Exception as e:
                self.logger.error(e)
        elif request['handle_way'] == 'selector':
            response.selector = Selector(text=response.text)

        return response

    def handle_error(self, request: Request, exception: Exception) -> Union[Request, None]:
        pass
