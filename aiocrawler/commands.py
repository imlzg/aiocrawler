# coding: utf-8
# Date      : 2019/4/26
# Author    : kylin
# PROJECT   : aiocrawler
# File      : aiocrawler
import sys
import argparse
from pathlib import Path
from pyclbr import readmodule
from importlib import import_module
from aiocrawler.settings import BaseSettings
logger = BaseSettings.LOGGER


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

        spider = get_module(args.name)
        if not spider:
            logger.error('The Spider name you provided is not found in this directory.')
            return

        try:
            run_module = import_module('run')
            run_module.run(spider)
        except Exception as e:
            logger.error(e)

    elif args.commands == "output" and args.filename:
        item_module = import_module('.items')


def get_module(name: str, spider_module_name: str = 'spiders'):

    module = None
    try:
        current_dir = str(Path('').cwd())
        if current_dir not in sys.path:
            sys.path.append(current_dir)

        spider_module = import_module(spider_module_name)

        for module_name in readmodule(spider_module_name).keys():
            module = getattr(spider_module, module_name)
            if name == vars(module).get(name, ''):
                return module
    finally:
        return module
