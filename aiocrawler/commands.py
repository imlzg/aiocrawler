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
from aiocrawler.extensions.templates import SpiderTemplate

logger = BaseSettings.LOGGER


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("commands", choices=["startproject", "run"], help="The Aiocrawler Commands")
    parser.add_argument('name', help="The Project Name you want to start")
    args = parser.parse_args()

    if args.commands == "startproject":
        tmpl = SpiderTemplate(args.name)
        tmpl.gen_project()
    elif args.commands == "run":
        spider = get_module(args.name)
        if not spider:
            logger.error('The Spider name you provided is not found in this directory.')
            return

        try:
            run_module = import_module('run')
            run_module.run(spider)
        except Exception as e:
            logger.error(e)


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
