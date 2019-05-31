# coding: utf-8
from typing import List, Union
from aiocrawler.request import Request
from aiocrawler.response import Response
from aiocrawler.settings import BaseSettings
from aiocrawler.log import logger


class Spider(object):
    name: str = None
    words: List[Union[float, str, int, bool]] = None

    def __init__(self, settings: BaseSettings):
        self.setting = settings
        self.logger = logger

    def make_request(self, word: str) -> Union[List[Request], Request]:
        raise NotImplementedError(
            '{} make_request method is not define'.format(self.__class__.__name__))

    def parse(self, response: Response):
        pass

    def handle_error(self, request: Request, exception: Exception) -> Union[Request, None]:
        pass
