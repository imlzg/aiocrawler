# coding: utf-8
from os import urandom
from ujson import dumps
from hashlib import sha1
from datetime import datetime
from typing import Union
from aiohttp_session import get_session
from aiohttp.web import Request, Response, HTTPFound
from aiocrawler.distributed.common import DATETIME_FORMAT

PERMISSIONS = ['Admin', 'superuser', 'user']


def jsonp(data: dict, callback: str) -> str:
    """
    json to jsonp
    :param data: json data
    :param callback: callback name
    :return: jsonp text
    """
    text = '{callback}({data})'.format(callback=callback, data=dumps(data))
    return text


def jsonp_response(request: Request, data: dict, status: int = 200):
    if 'callback' in request.query:
        return Response(text='{callback}({data})'.format(
            callback=request.query['callback'],
            data=dumps(data)),
            status=status)

    return Response(text=dumps(data), status=status)


def login_required(fn):
    async def wrapped(self, request: Request):
        app = request.app
        routers = app.router

        session = await get_session(request)

        if 'username' not in session:
            if request.method == 'GET' and 'callback' not in request.query:
                return HTTPFound(routers['login'].url_for())
            else:
                return jsonp_response(request, {
                    'status': 400,
                    'msg': 'Method not allowed'
                })

        return await fn(self, request)

    return wrapped


def gen_uuid(remote_ip: str, host: str, hostname: str) -> str:
    uuid = sha1()
    uuid.update(remote_ip.encode())
    uuid.update(host.encode())
    uuid.update(hostname.encode())
    uuid = uuid.hexdigest()
    return uuid


def gen_token() -> str:
    token = sha1(urandom(40)).hexdigest()
    return token


def gen_echarts_line_data(now: datetime, value: Union[int, float]):
    data = {
        'name': now.strftime(DATETIME_FORMAT),
        'value': [
            now.strftime(DATETIME_FORMAT),
            value
        ]
    }
    return data
