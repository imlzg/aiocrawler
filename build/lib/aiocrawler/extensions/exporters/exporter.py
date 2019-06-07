# coding: utf-8
# Date      : 2019/4/23
# Author    : kylin
# PROJECT   : aiocrawler
# File      : exporters
from aiocrawler.settings import BaseSettings
from typing import List
from aiocrawler.item import Item
from aiocrawler import Field
from aiocrawler import logger
from math import ceil


class BaseExporter(object):
    def __init__(self, settings: BaseSettings, item_class: Item):
        self.settings = settings
        self.logger = logger
        self.item_class = item_class
        self.item_class_name = item_class.__class__.__name__

    @staticmethod
    def chunk(items: List[Item], batch_size: int = 512):
        batch = int(ceil(len(items) / batch_size))
        for i in range(batch):
            yield items[i*batch_size:(i+1)*batch_size]

    @staticmethod
    def get_fields(item: Item):
        for field_name in item.__class__.__dict__:
            if isinstance(getattr(item.__class__, field_name), Field):
                yield field_name
