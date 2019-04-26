# coding: utf-8
from typing import Union, List
from json import loads
from parsel import Selector
from core.settings import BaseSettings
from core.request import Request
from core.response import Response


class Spider(object):
    def __init__(self, settings: BaseSettings):
        self.setting = settings
        self.logger = self.setting.LOGGER

    def make_request(self, word: str) -> Union[List[Request], Request]:
        return Request(url=word)

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
