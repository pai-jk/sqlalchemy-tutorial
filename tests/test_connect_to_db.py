"""
뭘 하고싶니?
connection 을 맺는 전 과정 테스트하며, 각 단계에서 시간이 얼마나 걸리는지를 확인해보자!
"""
import logging
import time

import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine


async def test_measure_elapsed_time_per_step(test_engine):
    # TIP: `❯ poetry add "sqlalchemy[asyncio]" : greenlet 까지 설치`
    # 애프리케이션 <-> sqlalchemy <-> connection pool <-(약 0.7초)> DB

    start_time = time.perf_counter()
    async with test_engine.connect() as conn:
        # 커넥션 풀 생성(시간이 훨씬 오래 걸림)
        elapsed_time = time.perf_counter() - start_time
        logging.info(f"(1) 첫번째 데이터 베이스 연결에 걸린 시간: {elapsed_time:.4f}s")  # 0.0720s

        start_time = time.perf_counter()
        await conn.execute(sqlalchemy.text("SELECT 1;"))
        elapsed_time = time.perf_counter() - start_time
        logging.info(f"(2) select query 날리는데 걸린 시간: {elapsed_time:.4f}s")  # 0.0030s

        # with문을 나갈때 자동으로 conn.close()
        # pool이 반환된다.

    start_time = time.perf_counter()
    async with test_engine.connect() as conn:
        # (1) 에서 생성한 커넥션 풀을 사용 0.0001s
        elapsed_time = time.perf_counter() - start_time
        logging.info(f"(1-1) 두번째 데이터 베이스 연결에 걸린 시간: {elapsed_time:.4f}s")


async def test_pool_recycle(test_engine):
    test_engine = create_async_engine(
        'postgresql+asyncpg://user:password@localhost:5434/testdb',
        echo=True,
        pool_pre_ping=True)
    # pool_recycle=1)
    # 오래된 커넥션 풀은 죽어있을 경우가 있음 그래서 pool_recycle 설정을 통해 커넥션이 죽는걸 방지

    start_time = time.perf_counter()
    async with test_engine.connect() as conn:
        elapsed_time = time.perf_counter() - start_time
        logging.info(f"(1-1) 첫번째 데이터 베이스 연결에 걸린 시간: {elapsed_time:.4f}s")

        start_time = time.perf_counter()
        await conn.execute(sqlalchemy.text("SELECT 1;"))
        elapsed_time = time.perf_counter() - start_time
        logging.info(f"(1-2) select query 날리는데 걸린 시간: {elapsed_time:.4f}s")
    # reset, transaction already reset
    # exceeded timeout; recycling

    time.sleep(2)

    # 재생성은 새로운 요청이 왔을때 진행된다.
    # pre_ping : 0.0112s
    # 미리 ping을 날려서 커넥션이 죽어있으면 새로운 커넥션을 생성
    start_time = time.perf_counter()
    async with test_engine.connect() as conn:
        elapsed_time = time.perf_counter() - start_time
        logging.info(f"(2-1) 첫번째 데이터 베이스 연결에 걸린 시간: {elapsed_time:.4f}s")

        start_time = time.perf_counter()
        await conn.execute(sqlalchemy.text("SELECT 1;"))
        elapsed_time = time.perf_counter() - start_time
        logging.info(f"(2-2) select query 날리는데 걸린 시간: {elapsed_time:.4f}s")


async def test_pool_size(launch_test_db):
    # locust 같은 툴을 사용한 부하 테스트 후, pool_size를 조정해야함
    test_engine = create_async_engine(
        'postgresql+asyncpg://user:password@localhost:5434/testdb',
        echo=True,
        pool_size=10,
        max_overflow=0,
        pool_timeout=1)

    conns = []
    for i in range(10):
        logging.info(f"{i}th create connection 생성")
        conns.append(await test_engine.connect())

    logging.info(f"11th create connection 생성.. timeout 걸림")
    logging.info(f"{conns}")

    await test_engine.connect()


async def test_set_statement_timeout(launch_test_db):
    test_engine = create_async_engine(
        'postgresql+asyncpg://user:password@localhost:5434/testdb',
        echo=True,
        connect_args={"server_settings": {"statement_timeout": "1000"}}  # 단위가 ms, 보통 15s 정도로 설정함
    )

    async with test_engine.connect() as conn:
        # 쿼리 지연 테스트 코드
        await conn.execute(sqlalchemy.text("SELECT pg_sleep(0.9);"))
