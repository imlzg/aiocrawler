# from aiocrawler import BaseSettings
# from aiocrawler.server.dashboard import Dashboard
#
#
# if __name__ == '__main__':
#     dashboard = Dashboard(BaseSettings())
#     dashboard.run()
from aiohttp import web
from aiocrawler import logger


async def main(request):
    resp = web.WebSocketResponse()
    await resp.prepare(request)
    async for msg in resp:
        logger.debug(msg.data)
    return resp

if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', main)
    ])
    web.run_app(app)
