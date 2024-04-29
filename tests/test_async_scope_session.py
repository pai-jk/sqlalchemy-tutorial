"""
커넥션 이후 쿼리의 맥락

트랜젝션
    쿼리를 날리고
    커밋까지 날려야 적용이 됨

위의 맥락이 세션
세션 메이커 -> 엔진이 받은 쿼리로 세션을 만들어줌
"""
import asyncio
import logging

from sqlalchemy import text

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine


async def test_show_same_pid(test_engine):
    session_factory = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    AsyncScopedSession = scoped_session(session_factory)
    """스레드가 1개의 세션을 공유하기 때문에 
    테스크 별로 세션을 사용하도록 해야한다. 
    """

    async def call0_function():
        await asyncio.sleep(0.1)
        async with AsyncScopedSession() as session:
            logging.info("call0_function >>>")
            result = await session.execute(text("SELECT pg_backend_pid()"))
            logging.info("call0_function end")
            return result.scalar()

    async def call1_function():
        await asyncio.sleep(0.5)
        async with AsyncScopedSession() as session:
            logging.info("call1_function >>>")
            result = await session.execute(text("SELECT pg_backend_pid()"))
            logging.info("call1_function end")
            return result.scalar()

    task1 = asyncio.create_task(call0_function())
    task2 = asyncio.create_task(call1_function())

    output0, output1 = await asyncio.gather(task1, task2)
    assert output0 == output1


async def test_show_async_scoped_session(test_engine):
    test_engine = create_async_engine(
        'postgresql+asyncpg://user:password@localhost:5434/testdb',
        echo=True,
        pool_size=2,
        max_overflow=0)

    async_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    AsyncScopedSession = async_scoped_session(async_session_factory, scopefunc=asyncio.current_task)
    """비동기는 경합 상황에 대한 처리가 제일 중요함
    pool에서 커넥션을 가져와서 세션을 통해 쿼리를 동작, 동작이 끝나면 커넥션을 반환
    """

    async def call0_function():
        logging.info(f"call0_function task id : {asyncio.current_task()}")
        # await asyncio.sleep(0.1)
        async with AsyncScopedSession() as session:
            logging.info("call0_function >>>")
            result = await session.execute(text("SELECT pg_backend_pid()"))
            logging.info("call0_function end")
            return result.scalar()

    async def call1_function():
        # await asyncio.sleep(0.5)
        logging.info(f"call1_function task id : {asyncio.current_task()}")
        async with AsyncScopedSession() as session:
            logging.info("call1_function >>>")
            result = await session.execute(text("SELECT pg_backend_pid()"))
            logging.info("call1_function end")
            return result.scalar()

    task1 = asyncio.create_task(call0_function())
    task2 = asyncio.create_task(call1_function())

    output0, output1 = await asyncio.gather(task1, task2)
    assert output0 != output1
