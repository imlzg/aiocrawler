# coding: utf-8
# Date      : 2019/4/26
# Author    : kylin
# PROJECT   : aiocrawler
# File      : test
#              ┏┓   ┏┓
#            ┏┛┻━━━┛┻┓
#            ┃   ☃   ┃
#            ┃ ┳┛ ┗┳ ┃
#            ┃   ┻   ┃
#            ┗━┓   ┏━┛
#              ┃   ┗━━━┓
#              ┃神兽保佑┣┓
#              ┃永无BUG!┏┛
#              ┗┓┓┏━┳┓┏┛
#               ┃┫┫  ┃┫┫
#               ┗┻┛  ┗┻┛
import asyncio
import signal


stop = False


async def test():
    while True:

        print('test')
        await asyncio.sleep(1)


def signal_int(signum, frame):
    global stop
    stop = True
    print('press signal int')
    tasks = asyncio.Task.all_tasks()
    for task in tasks:
        task.cancel()
    loop.stop()


signal.signal(signal.SIGINT, signal_int)

loop = asyncio.get_event_loop()
try:
    for _ in range(10):
        asyncio.ensure_future(test())
    loop.run_forever()
finally:
    loop.close()
