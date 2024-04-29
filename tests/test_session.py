"""
orm object relational mapping

디비의 테이블을 클래스의 하나의 객체로 매핑하는것
그 클래스를 Entity 또는 Model이라고 함

상태값
transient : 객체가 생성되었지만 아직 세션에 추가되지 않은 상태, entity 만 만든 상태
    entity.i
pending : 세션에 추가된 상태, orm에서만 관리하고 있음
    sess.add(entity)
persistent : 세션에 추가되어서 관리되는 상태,
    sees.flush() : send 쿼리 날림
    sess.commit() : db에 저장
expired : 해당 객체에 대한 상태
detached : 세션 아웃

트랜잭션의 격리수준(isolation level)
 - read commited
 - read uncommited
 ...

"""
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, async_scoped_session
from sqlalchemy import inspect

from src.models import UserEntity
import logging


async def test_add_journey(test_engine, with_tables):
    """ add -> flush -> commit -> refresh 순으로 호출

    실제로 entity의 상태가 어떻게 변하는지 확인
    :param test_engine:
    :return:
    """
    async_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    # commit 시에 expired = true가 됨.
    # expire_on_commit=False로 설정하면, commit 이후에도 expired = true가 되지않아서 데이터에 대한 접근이 가능함
    # 다만 이 방법은 expire 문제를 야기할수 있음
    session_factory = async_scoped_session(async_session_factory, scopefunc=asyncio.current_task)

    logging.info("\ninitialize >>>")
    given_user0 = UserEntity(id=None, name="test0")  # 엔터티 생성
    show_entity_status(given_user0)

    async with session_factory() as session:
        logging.info("\nadd >>>")
        session.add(given_user0)
        show_entity_status(given_user0)

        logging.info("\nflush >>>")
        await session.flush([given_user0])
        show_entity_status(given_user0)

        logging.info("\ncommit >>>")
        await session.commit()
        show_entity_status(given_user0)

        logging.info("\nrefresh >>>")
        await session.refresh(given_user0)
        show_entity_status(given_user0)

        logging.info("\nout >>>")
    logging.info("\nclosed >>>")
    show_entity_status(given_user0)


def show_entity_status(entity):
    inspector = inspect(entity)
    logging.info(f"- Transient:{inspector.transient}")
    logging.info(f"- Pending:{inspector.pending}")
    logging.info(f"- Persistent:{inspector.persistent}")
    logging.info(f"- Expired:{inspector.expired}")
    logging.info(f"- Detached:{inspector.detached}")
