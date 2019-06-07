# coding: utf-8
import sys
from loguru import logger


logger.remove()
fmt = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | " \
      "<level>{level}</level> | " \
      "<cyan>{name}</cyan> <line {line}>: <level>{message}</level>"
logger.add(sys.stdout, format=fmt)
# logger.add('log/aio-crawler.log', format=fmt, rotation='10 MB')

logger = logger
