# coding: utf-8
# Date      : 2019/4/26
# Author    : kylin
# PROJECT   : aiocrawler
# File      : aiocrawler
import argparse
from core.extensions.templates import SpiderTemplate


def commands():
    parser = argparse.ArgumentParser()
    parser.add_argument("commands", choices=["startproject", ], help="The Aiocrawler Commands")
    parser.add_argument('--name', "-n", help="The Project Name you want to start")
    args = parser.parse_args()

    if args.commands == "startproject":
        tmpl = SpiderTemplate(args.name)
        tmpl.gen_project()
