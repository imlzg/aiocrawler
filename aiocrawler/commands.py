# coding: utf-8
# Date      : 2019/4/26
# Author    : kylin
# PROJECT   : aiocrawler
# File      : aiocrawler
import os
import argparse
from aiocrawler.engine import Engine
from aiocrawler.utils import get_setting, get_spider, get_item
from aiocrawler.extensions.templates import SpiderTemplate
from aiocrawler import logger


def main():
    """
    Usage:
        aiocrawler run (<name>)
        aiocrawler startproject (<name>)
        aiocrawler output (<name>)  [-i item_name --item-name=item_name]
                                    [-t output_type --type=output_type]
                                    [-f filename, --filename=filename]
        aiocrawler -h | --help
        aiocrawler --version
    Options:
        -h --help   show this help
        -v --version    show current version
        run     run a aiocrawler project
        startproject    create a new aiocrawler project
        output      output the item from the project
        name    project name
        -i item_name --item-name=item_name     the item name from the items.py
        --type=output_type     output type, support mongo and csv now [default: mongo,csv]
        -f filename, --filename=filename  csv filename
    Example:
        aiocrawler startproject demo
        aiocrawler run demo
        aiocrawler output demo --item-name=demo --type=mongo
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("commands", choices=["startproject", "run", "output"], help="The Aiocrawler CLI")
    parser.add_argument('project_name', help="The Project Name", default=None)
    parser.add_argument('--setting_name', '-s',  help='The setting name', default=None)
    parser.add_argument('--filename', '-f', help='The csv filename', default=None)
    parser.add_argument('--item', '-i', help='the item name from the items.py', default=None)
    parser.add_argument('--type', '-t', choices=['csv', 'mongo'],
                        help='output type, support mongo and csv now', default=None)
    parser.add_argument('--batch_size', '-b', help='batch size', default=1000, type=int)
    parser.add_argument('--table_name', '-tb', help='Mongo table name', default=None)
    args = parser.parse_args()

    if args.commands == "startproject" and args.project_name:

        tmpl = SpiderTemplate(args.project_name)
        tmpl.gen_project()
    elif args.commands == "run" and args.project_name:
        run_spider(args.project_name, args.setting_name)

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
    settings = get_setting(project_name)

    if output_type is None:
        mongo_host = settings.MONGO_HOST or os.environ.login_get('MONGO_HOST', None)
        if mongo_host:
            output_type = 'mongo'
        else:
            output_type = 'csv'

    if output_type not in ['csv', 'mongo']:
        logger.error('Unknown output type: {type}', type=output_type)
        return

    item_class = get_item(item_name)
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


def run_spider(spider_name: str, setting_name: str):
    settings = get_setting(setting_name)()
    spider = get_spider(spider_name)(settings)
    if not spider or not settings:
        logger.error('The project name you provided is not found in this directory.')
        return
    engine = Engine(settings=settings, spider=spider)
    engine.run()
