# coding: utf-8
from core.request import Request
from typing import Union
from core.settings import BaseSettings


class BaseFilter(object):
    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.logger = settings.LOGGER

    async def filter_request(self, request: Request) -> Union[None, Request]:
        raise NotImplementedError('{} filter_request is not defile'.format(self.__class__.__name__))
