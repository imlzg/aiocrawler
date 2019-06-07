# coding: utf-8
# Date      : 2019/4/25
# Author    : kylin
# PROJECT   : aiocrawler
# File      : allowed_code_middleware
from aiocrawler import Request
from aiocrawler import Response
from aiocrawler.middlewares.middleware import BaseMiddleware


class AllowedCodesMiddleware(BaseMiddleware):

    def process_response(self, request: Request, response: Response):
        if not 200 <= response.status <= 301 and response.status not in self.settings.ALLOWED_CODES:
            self.logger.debug('The response status <{code}> is not in ALLOWED_CODES', code=response.status)

            retry_count = request.meta.login_get('retry_count', 0)
            retry_count += 1

            request.meta['retry_count'] = retry_count
            return request
