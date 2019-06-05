import asyncio
from os import urandom
from hashlib import sha1
from typing import Union
from pathlib import Path
from time import sleep
from aiocrawler import logger
from aiohttp import ClientSession
from aiohttp.cookiejar import CookieJar


async def download(save_path: Union[str, Path],
                   url: str = None,
                   number: int = 2000,
                   delay: float = 0.1,
                   prefix: str = None,
                   img_type: str = 'jpg',
                   timeout: float = 10,
                   generator=None):

    prefix = prefix if prefix else sha1(urandom(40)).hexdigest()
    session = ClientSession(cookie_jar=CookieJar(unsafe=True))
    tasks = []
    if url:
        tasks = [
            asyncio.ensure_future(_download(url, save_path, ix, prefix, img_type, delay, timeout, session))
            for ix in range(number)
        ]
    elif generator:
        for ix, (url, cookies) in enumerate(generator):
            tasks.append(asyncio.ensure_future(_download(url,
                                                         save_path,
                                                         ix,
                                                         prefix,
                                                         img_type,
                                                         delay,
                                                         timeout,
                                                         session,
                                                         cookies)))

    if len(tasks):
        count = 0
        success = 0
        results = await asyncio.wait(tasks)
        for result in results[0]:
            result = result.result()
            count += 1
            if result:
                success += 1

        logger.success('Downloaded {prefix}: {count} images, {success} saved',
                       prefix=prefix,
                       count=count,
                       success=success)


async def _download(url: str,
                    save_path: Union[str, Path],
                    ix: int,
                    prefix: str,
                    img_type: str,
                    delay: float,
                    timeout: float,
                    session: ClientSession,
                    cookies=None):
    save_path = Path(save_path)
    filename = save_path / ('{prefix}_{ix}.{img_type}'.format(prefix=prefix, ix=ix, img_type=img_type))

    i = 1
    while filename.is_file():
        filename = save_path / ('{stem}_{i}{suffix}'.format(stem=filename.stem, i=i, suffix=filename.suffix))
        i += 1

    sleep(delay)
    async with session.get(url, timeout=timeout, cookies=cookies) as resp:
        if resp.status == 200:
            with filename.open('wb') as fb:
                fb.write(await resp.read())
                return True
