# coding: utf-8
import sys
from pathlib import Path
from typing import Type
from aiocrawler.spider import Spider
from aiocrawler.item import Item
from aiocrawler.settings import BaseSettings
from importlib import import_module

CURRENT_DIR = str(Path().absolute())
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)


def get_spider(spider_name: str, module_name: str = 'spiders') -> Type[Spider]:
    """
    get spider
    :param module_name: module name, 'spiders' by default
    :param spider_name: spider name
    :return: spider module
    """
    import_module(module_name)
    spiders = Spider.__subclasses__()
    for spider in spiders:
        if vars(spider).get('name', None) == spider_name:
            return spider


def get_setting(setting_name: str = None, module_name: str = 'settings') -> Type[BaseSettings]:
    """
    get setting
    :param setting_name: setting name
    :param module_name:
    :return:
    """
    import_module(module_name)
    settings = BaseSettings.__subclasses__()

    for setting in settings:
        if setting_name is None or vars(setting).get('PROJECT_NAME', None) == setting_name:
            return setting


def get_item(item_name: str = None, module_name: str = 'items') -> Type[Item]:
    """
    :param item_name:
    :param module_name:
    :return:
    """
    import_module(module_name)
    items = Item.__subclasses__()
    for item in items:
        if item_name is None or vars(item).get('item_name', None) == item_name:
            return item
