"""
관계형 테이블을 어떻게 entity로 표현할것인가
@dataclass
class User:
    id: Optional[int]
    name: str
    posts: List['Post']

    @staticmethod
    def new(name: str):
        return User(id=None, name=name, posts=[])

user.posts를 호출하면 해당 user의 post들을 가져온다.

@dataclass
class Post:
    id: Optional[int]
    user_id: str
    title: str

    @staticmethod
    def new(user_id: str, title: str):
        return Post(id=None, user_id=user_id, title=title)

post.user를 호출하면 해당 post의 user를 가져온다.


SQL MODEL
"""
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models import UserEntity, PostEntity
import logging


async def test_select_with_relationship(test_scoped_session):
    """
    """
    # given case
    async with test_scoped_session() as session:
        entity = UserEntity(id=None, name="test0")
        session.add(entity)
        await session.commit()
        await session.refresh(entity)
        user0_id = entity.id

        session.add(PostEntity(id=None, user_id=user0_id, title="title0"))
        session.add(PostEntity(id=None, user_id=user0_id, title="title1"))
        session.add(PostEntity(id=None, user_id=user0_id, title="title2"))
        await session.commit()

        entity = UserEntity(id=None, name="test1")
        session.add(entity)
        await session.commit()
        await session.refresh(entity)
        user1_id = entity.id

        session.add(PostEntity(id=None, user_id=user1_id, title="title3"))
        session.add(PostEntity(id=None, user_id=user1_id, title="title4"))
        session.add(PostEntity(id=None, user_id=user1_id, title="title5"))
        await session.commit()

    logging.info("\nwithout eager loading >>>")
    async with test_scoped_session() as session:
        logging.info("\ncreate stmt >>>")
        stmt = select(UserEntity)
        logging.info("\nsession execute >>>")
        result = await session.execute(stmt)
        user_entities = result.scalars().all()

        logging.info("\nget post >>>")
        for user_entity in user_entities:
            logging.info(f"\n  -get post(user_id:{user_entity.id}) >>>")
            post_entities = await user_entity.awaitable_attrs.posts
            # 조회 할때마다만 쿼리가 발생함
            # 모두 조회 시 N+1 문제가 발생

    logging.info("\nwith eager loading >>>")
    async with test_scoped_session() as session:
        logging.info("\ncreate stmt >>>")
        # selectinload : 테이블 마다 쿼리 한방씩
        # -> 테이블 마다 한번의 쿼리문이 발생하게 됨
        # joininload : join을 통해 한번에 가져옴
        # -> 1대N의 경우 중복된 값이 많아져 네트워크 비용이 늘어남
        stmt = select(UserEntity).options(selectinload(UserEntity.posts))
        logging.info("\nsession execute >>>")
        result = await session.execute(stmt)
        user_entities = result.scalars().all()
        # join시 중복 처리를 해줘야함
        # user_entities = result.scalars().unique().all()

        logging.info("\nget posts >>>")
        for user_entity in user_entities:
            logging.info(f"\n  -get post(user_id:{user_entity.id}) >>>")
            post_entities = user_entity.posts
