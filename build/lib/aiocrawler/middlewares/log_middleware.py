# coding: utf-8
from aiocrawler import BaseSettings
from aiocrawler.engine import Engine
from aiocrawler.middlewares import BaseMiddleware


class LogMiddleware(BaseMiddleware):
    def __init__(self, settings: BaseSettings, engine: Engine):
        BaseMiddleware.__init__(self, settings, engine)
