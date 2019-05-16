<div align="left">
<img src="https://github.com/kylin1020/aiocrawler/blob/master/logo.png" height="128" width="128" >
 </div>

![version](https://img.shields.io/badge/version-v1.22-green.svg)
![support](https://img.shields.io/badge/python-3.6%20%7C%203.7-blue.svg)
![license](https://img.shields.io/badge/license-MIT-yellow.svg)

#### Aiocrawler 是一个基于asyncio协程的分布式异步爬虫框架

![image](https://github.com/kylin1020/aiocrawler-demo/blob/master/credit.gif)


- [中文文档][doc_cn] | [documentation][doc_en]
- ### 安装方式
```bash
pip3 install aiocrawler
```
或者直接下载源代码并执行以下命令
```bash
python3 setup.py install
```

- ### 创建一个新项目
```bash
aiocrawler startproject demo
```
**上述命令执行后将在当前目录下生成dmeo目录，包含如下文件**
```
+-- demo/
|    +-- items.py
|    +-- middlewares.py
|    +-- settings.py
|    +-- spiders.py
```
**编写第一个Spider**
```python
# coding: utf-8
from aiocrawler import BaseSettings, Spider, Request


class DemoSpider(Spider):
    name = "demo"

    def __init__(self, settings: BaseSettings):
        Spider.__init__(self, settings)

    def make_request(self, word):
        return Request(word, callback=self.parse)

    def parse(self, response):
        pass
```
**在settings.py中配置一些信息**
```python
# coding: utf-8
from aiocrawler import BaseSettings
from demo.middlewares import DemoMiddleware


class DemoSettings(BaseSettings):
    PROJECT_NAME = 'demo'

    """
    If you use the redis server as the scheduler, the REDIS_URL must be configured.
    """
    REDIS_URL = 'redis://user:password@redis_address:port'
    REDIS_PROJECT_NAME = 'demo'

    CONCURRENT_REQUESTS = 32
    CONCURRENT_WORDS = 32
    DEFAULT_TIMEOUT = 20
    DEFAULT_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN',
    }

    DOWNLOAD_DALEY = 0
    PROCESS_DALEY = 0.01
    MIDDLEWARES = [
        (DemoMiddleware, 300)
    ]
```
**编写中间件，扩展功能**
```python
from aiocrawler.middlewares import BaseMiddleware


class DemoMiddleware(BaseMiddleware):
    def process_request(self, request):
        pass

    def process_response(self, request, response):
        pass

    def process_exception(self, request, exception):
        pass

    def process_item(self, item):
        pass
```
**Aiocrawler没有区分下载器中间件和爬虫中间件
但提供了四种方法: process_request, process_exception, process_response, process_item.**
### Aiocrawler支持以异步方式编写中间件
**我们推荐使用异步方式编写中间件**
**因为这是非阻塞的，并且可以结合大多数异步库，比如aiomysql、aioredis**
```python
from aiocrawler.middlewares import BaseMiddleware


class DemoMiddleware(BaseMiddleware):
    async def process_request(self, request):
        pass

    async def process_response(self, request, response):
        pass

    async def process_exception(self, request, exception):
        pass

    async def process_item(self, item):
        pass
```
**要激活中间件，只需要在settings.py中导入并配置MIDDLEWARES即可**
````python
from aiocrawler import BaseSettings
from demo.middlewares import DemoMiddleware


class DemoSettings(BaseSettings):
    PROJECT_NAME = 'demo'
    
    # other information...
    MIDDLEWARES = [
        (DemoMiddleware, 300)
    ]
````
**编写Item类** 
```python
from aiocrawler import Item, Field


class DemoItem(Item):
    """
    you can define your Item like this, just like scrapy Item:
    name = Field()
    website = Field()
    """
    item_name = "demo"
    pass
```
### 运行爬虫
```bash
aiocrawler run demo
```
### 将爬取到的Item导出到csv文件或者mongodb
```bash
aiocrawler output demo
```
**如果在settings.py中配置了MONGO_HOST，Aiocrawler将默认导出到mongodb**
```python
from aiocrawler import BaseSettings
from demo.middlewares import DemoMiddleware


class DemoSettings(BaseSettings):
    PROJECT_NAME = 'demo'
    
    # other information...
    MONGO_HOST = 'your mongo sever address'
    MONGO_PORT = 27017
    MONGO_USER = "mongo username"
    MONGO_PASSWORD = "mongo password"
    MONGO_DB = None # If you configure MONGO_HOST in your settings or the Environmental variables, it will be exported to mongo sever by default.    

```
**也可以指定导出方式**
```bash
aiocrawler output demo --filename data.csv --type csv
```
**指定导出到mongodb**
```bash
aiocrawler output demo --type mongo
```
[doc_cn]: #
[doc_en]: https://github.com/kylin1020/aiocrawler/blob/master/README.md

