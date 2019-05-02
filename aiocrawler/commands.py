# coding: utf-8
# Date      : 2019/4/26
# Author    : kylin
# PROJECT   : aiocrawler
# File      : aiocrawler
import sys
import argparse
from pathlib import Path
from importlib import import_module
from aiocrawler.settings import BaseSettings
logger = BaseSettings.LOGGER

current_dir = str(Path('').cwd())
if current_dir not in sys.path:
    sys.path.append(current_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("commands", choices=["startproject", "run", "output"], help="The Aiocrawler Commands")
    parser.add_argument('name', help="The Project Name", default=None)
    parser.add_argument('--filename', '-f', help='The Filename', default=None)
    parser.add_argument('--item', '-i', help='The Item you want to output, output all items by default.', default=None)
    args = parser.parse_args()

    if args.commands == "startproject" and args.name:
        from aiocrawler.extensions.templates import SpiderTemplate

        tmpl = SpiderTemplate(args.name)
        tmpl.gen_project()
    elif args.commands == "run" and args.name:
        run_spider(args.name)

    elif args.commands == "output":
        output(filename=args.filename, item_name=args.item)


def output(filename: str = None, item_name: str = None):
    item_class = None
    from aiocrawler import Item, BaseSettings
    from aiocrawler.extensions.exporters.redis_to_file import RedisToFile

    item_subclasses = get_subclass(Item, 'items')
    for sub in item_subclasses:
        if item_name and vars(sub).get('item_name', None) == item_name or vars(sub).get('item_name', None):
            item_class = sub()
            break

    settings_subclasses = get_subclass(BaseSettings, 'settings')
    if len(settings_subclasses) and isinstance(item_class, Item):
        settings = settings_subclasses[0]()

        r = RedisToFile(settings, item_class, filename=filename)
        r.run()


def run_spider(name: str):
    from aiocrawler import Spider
    spider = None
    subclasses = get_subclass(Spider, 'spiders')
    for subclass in subclasses:
        if vars(subclass).get('name', None) == name:
            spider = subclass
            break

    if not spider:
        logger.error('The Spider name you provided is not found in this directory.')
        return
    try:
        run_module = import_module('run')
        run_module.run(spider)
    except Exception as e:
        logger.error(e)


def get_subclass(class_type: type, module: str, subclass_name: str = None):
    try:
        import_module(module)
    finally:
        pass
    data = class_type.__subclasses__()

    if subclass_name:
        for sub_class in data:
            if sub_class.__name__ == subclass_name:
                data = sub_class
                break

    return data

