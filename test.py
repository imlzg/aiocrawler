import asyncio
import aiojobs


async def test():
    print('test')
    await asyncio.sleep(30)
    print('done')


async def main():
    scheduler = await aiojobs.create_scheduler()
    await scheduler.spawn(test())

    await asyncio.sleep(2)
    await scheduler.close()


if __name__ == '__main__':
    asyncio.run(main())
