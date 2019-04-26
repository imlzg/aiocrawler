# coding: utf-8
# Date      : 2019-04-25
# PROJECT   : company
# File      : run.py
import sys
sys.path.append('../..')
from core.engine import Engine
from demo.company.spiders import CompanySpider
from demo.company.settings import CompanySettings
from demo.company.middlewares import CompanyMiddleware

if __name__ == "__main__":
    settings = CompanySettings()
    spider = CompanySpider(settings)
    middleware = CompanyMiddleware(settings)

    engine = Engine(spider=spider,
                    settings=settings,
                    downloader_middlewares=[
                        (middleware, 300)
                    ])
    engine.run()
