# coding: utf-8
from http.cookies import SimpleCookie
from parsel.selector import Selector


class Response(object):
    def __init__(self, text: str, status: int, cookies: SimpleCookie):
        self.text = text
        self.status = status
        self.cookies = cookies
        self.json: dict = {}
        self.selector: Selector = None
        self.meta: dict = {}
