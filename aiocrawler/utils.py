# coding: utf-8
import sys
import pyclbr
from pathlib import Path
from aiocrawler.spider import Spider
from aiocrawler.item import Item
from aiocrawler.settings import BaseSettings
from importlib import import_module

CURRENT_DIR = str(Path().absolute())
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)


def get_spider(spider_name: str = None, module: str = 'spiders', classname: str = None):
    """
    get spider
    :param classname:
    :param module: module name, 'spiders' by default
    :param spider_name: spider name
    :return: spider module
    """
    return get_module(module_name=module, super_class=Spider, key='name', name=spider_name, classname=classname)


def get_setting(setting_name: str = None, module: str = 'settings', classname: str = None):
    """
    get setting
    :param classname:
    :param setting_name: setting name
    :param module:
    :return:
    """
    return get_module(module_name=module,
                      super_class=BaseSettings,
                      key='PROJECT_NAME',
                      name=setting_name,
                      classname=classname)


def get_item(item_name: str = None, module: str = 'items', classname: str = None):
    """
    :param classname:
    :param item_name:
    :param module:
    :return:
    """
    return get_module(module_name=module, super_class=Item, key='item_name', name=item_name, classname=classname)


def get_module(module_name: str, super_class: type, key: str, name: str, classname: str):
    ms = import_module(module_name)

    if classname and classname in vars(ms):
        return getattr(ms, classname)
    else:
        for m_name in vars(ms).keys():
            module = getattr(ms, m_name)
            if isinstance(module, type) and issubclass(module, super_class) and (vars(module).get(key, None) == name):
                return module
