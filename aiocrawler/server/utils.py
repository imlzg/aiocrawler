# coding: utf-8
from os import urandom
from ujson import dumps
from hashlib import sha1
from aiohttp_session import get_session
from aiohttp.web import Request, Response, json_response, HTTPFound


def jsonp(data: dict, callback: str) -> str:
    """
    json to jsonp
    :param data: json data
    :param callback: callback name
    :return: jsonp text
    """
    text = '{callback}({data})'.format(callback=callback, data=dumps(data))
    return text


def json_or_jsonp_response(request: Request, data: dict):
    if 'callback' in request.query:
        return Response(text=jsonp(data, request.query.get('callback', 'callback')))
    return json_response(data)


def login_required(fn):
    async def wrapped(self, request: Request, *args, **kwargs):
        app = request.app
        routers = app.router

        session = await get_session(request)

        if 'username' not in session:
            if request.method == 'GET' and 'callback' not in request.query:
                return HTTPFound(routers['login'].url_for())
            else:
                return json_or_jsonp_response(request, {
                    'status': 400,
                    'msg': 'Method not allowed'
                })

        return await fn(self, request, *args, **kwargs)

    return wrapped


def gen_uuid(remote_ip: str, host: str, hostname: str) -> str:
    uuid = sha1()
    uuid.update(remote_ip.encode())
    uuid.update(host.encode())
    uuid.update(hostname.encode())
    uuid = uuid.hexdigest()
    return uuid


def gen_token() -> str:
    token = sha1(urandom(32)).hexdigest()
    return token


DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
PERMISSIONS = {
    'admin': 0,
    'superuser': 1,
}
