import asyncio
from datetime import datetime

async def task(args):
    print(f"started {args} {datetime.now()}")
    await asyncio.sleep(args)  
    print(f"ended {args} {datetime.now()}")

async def main():
    # Run all tasks concurrently
    await asyncio.gather(
        task(1),
        task(3),
        task(5)
    )

asyncio.run(main())
