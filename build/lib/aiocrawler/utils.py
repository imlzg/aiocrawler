# coding: utf-8
import sys
from pathlib import Path
from aiocrawler.spider import Spider
from aiocrawler.item import Item
from aiocrawler.settings import BaseSettings
from importlib import import_module

CURRENT_DIR = str(Path().absolute())
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)


def get_spider(spider_name: str = None, module_name: str = 'spiders', classname: str = None):
    """
    get spider
    :param classname:
    :param module_name: module name, 'spiders' by default
    :param spider_name: spider name
    :return: spider module
    """
    return get_module(module_name=module_name, module_type=Spider, key='name', name=spider_name, classname=classname)


def get_setting(setting_name: str = None, module_name: str = 'settings', classname: str = None):
    """
    get setting
    :param classname:
    :param setting_name: setting name
    :param module_name:
    :return:
    """
    return get_module(module_name=module_name,
                      module_type=BaseSettings,
                      key='PROJECT_NAME',
                      name=setting_name,
                      classname=classname)


def get_item(item_name: str = None, module_name: str = 'items', classname: str = None):
    """
    :param classname:
    :param item_name:
    :param module_name:
    :return:
    """
    return get_module(module_name=module_name, module_type=Item, key='item_name', name=item_name, classname=classname)


def get_module(module_name: str, module_type: type, key: str = None, name: str = None, classname: str = None):
    ms = import_module(module_name)

    if classname and classname in vars(ms):
        return getattr(ms, classname)
    else:
        for m_name in vars(ms).keys():
            module = getattr(ms, m_name)
            if isinstance(module, type) and issubclass(module, module_type) and (vars(module).get(key, None) == name):
                return module
