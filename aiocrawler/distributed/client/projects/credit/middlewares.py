# coding: utf-8
# Date      : 2019-04-28
# PROJECT   : credit
# File      : middlewares.py
from aiocrawler.middlewares import BaseMiddleware


class CreditMiddleware(BaseMiddleware):
    def process_request(self, request):
        print(self.engine.__class__.__name__)

    def process_response(self, request, response):
        if response.json is None:
            self.logger.debug('Data error')
            request['dont_filter'] = True
            return request

    def process_exception(self, request, exception):
        request['dont_filter'] = True
        return request
