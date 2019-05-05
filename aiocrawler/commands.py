# coding: utf-8
# Date      : 2019/4/26
# Author    : kylin
# PROJECT   : aiocrawler
# File      : aiocrawler
import argparse
import os
import sys
import traceback
from importlib import import_module
from pathlib import Path

from aiocrawler import BaseSettings

logger = BaseSettings.LOGGER

current_dir = str(Path('').cwd())
if current_dir not in sys.path:
    sys.path.append(current_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("commands", choices=["startproject", "run", "output"], help="The Aiocrawler Commands")
    parser.add_argument('project_name', help="The Project Name", default=None)
    parser.add_argument('--filename', '-f', help='The Filename', default=None)
    parser.add_argument('--item', '-i', help='The Item you want to output, output all items by default.', default=None)
    parser.add_argument('--type', '-t', choices=['csv', 'mongo'],
                        help='the Item output type(local csv/remote mongo)', default=None)
    parser.add_argument('--batch_size', '-b', help='Batch size', default=1000, type=int)
    parser.add_argument('--table_name', '-tb', help='Table name', default=None)
    args = parser.parse_args()

    if args.commands == "startproject" and args.project_name:
        from aiocrawler.extensions.templates import SpiderTemplate

        tmpl = SpiderTemplate(args.project_name)
        tmpl.gen_project()
    elif args.commands == "run" and args.project_name:
        run_spider(args.project_name)

    elif args.commands == "output":
        output(project_name=args.project_name,
               filename=args.filename,
               item_name=args.item,
               output_type=args.type,
               batch_size=args.batch_size,
               table_name=args.table_name)


def output(project_name: str,
           filename: str = None,
           item_name: str = None,
           output_type: str = 'csv',
           batch_size: int = 1000, **kwargs):
    settings = None
    settings_subclasses = get_subclass(BaseSettings, 'settings')
    for sub in settings_subclasses:
        if vars(sub).get('PROJECT_NAME', '') == project_name:
            settings = sub
            break

    if output_type is None:
        mongo_host = settings.MONGO_HOST or os.environ.get('MONGO_HOST', None)
        if mongo_host:
            output_type = 'mongo'
        else:
            output_type = 'csv'

    if output_type not in ['csv', 'mongo']:
        logger.error('Unknown output type: {type}', type=output_type)
        return

    from aiocrawler import Item
    item_subclasses = get_subclass(Item, 'items')
    item_class = None

    item_name = item_name if item_name else project_name
    for sub in item_subclasses:
        if item_name and vars(sub).get('item_name', None) == item_name:
            item_class = sub
            break
    if item_class is None:
        for sub in item_subclasses:
            if vars(sub).get('item_name', None):
                item_class = sub
                break

    if settings and item_class:
        if output_type == 'csv':
            from aiocrawler.extensions.exporters import RedisToFile
            r = RedisToFile(settings=settings(), item_class=item_class(), filename=filename, batch_size=batch_size)
            r.run()
        elif output_type == 'mongo':
            from aiocrawler.extensions.exporters import RedisToMongo
            r = RedisToMongo(settings=settings(), item_class=item_class(),
                             table_name=kwargs.get('table_name', None), batch_size=batch_size)
            r.run()
    else:
        logger.error('The item name or project name you provided is not exists in this directory.')


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
        logger.error(traceback.format_exc(limit=10))


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
