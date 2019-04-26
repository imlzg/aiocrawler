# coding: utf-8


class Request(dict):
    def __init__(self, url: str,
                 method: str = 'GET',
                 params: dict = None,
                 dont_filter: bool = False,
                 proxy: str = None,
                 err_callback=None,
                 encoding: str = None,
                 headers: dict = None,
                 format_type: str = 'selector',
                 timeout: int = None,
                 meta: dict = None,
                 cookies: dict = None,
                 callback=None):
        dict.__init__(self)

        self['url'] = url
        self['method'] = method if method in ['GET', 'POST'] else 'GET'
        self['proxy'] = proxy
        self['dont_filter'] = dont_filter
        self['params'] = params

        self['callback'] = callback.__name__ if callback else 'parse'
        self['err_callback'] = err_callback.__name__ if err_callback else 'handle_error'

        self['timeout'] = timeout
        self['headers'] = headers

        self['encoding'] = encoding
        self['cookies'] = cookies
        self['meta'] = meta

        if format_type in ['text', 'json', 'selector']:
            self['handle_way'] = format_type
        else:
            self['handle_way'] = 'selector'
