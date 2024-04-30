# sqlalchemy-tutorial
https://github.com/craftsangjae/sqlalchemy-tutorial 레포지토리를 학습한 내용입니다.

해당 래포지토리는 sqlalchemy 패키지를 이용하여 다음과 같은 동작을 이해하는 목적을 가진다.

1. 데이터베이스 connection 동작과 connection pool의 동작
2. 세션과, 비동기 동작에서 스레드와 테스크. 
3. orm Entity의  각 상태
4. orm Entity에서 관계형 데이터베이스의 테이블을 가져오는 방법 



## 1. 데이터베이스 connection 동작과 connection pool의 동작

보통의 3티어 형태의 서비스에선 대부분의 동작 시간을 데이터베이스와의 연결이 차지. 때문에 서비스의 성능이 데이터베이스와의 연결이 얼마나 빠르고 정확하게 이뤄지는지에의해 결정.



### 애플리케이션과 데이터베이스의 상호작용 순서

1. 애플리케이션에서 데이터베이스로 커넥션을 요청
   - 이때 이전에 사용한 커넥션을 재사용하기 위해 커넥션 풀에 저장된 커넥션을 사용
2. 가져온 커넥션으로 세션이라는 통신 채널을 시작
   - 세션을 통해 쿼리, 트렌젝션 관리등을 수행
3. 커넥션 반환 및 세션 종료
   - 작업이 완료되면 커넥션을 커넥션 풀에 반환하고 세션을 종료



- 커넥션을 재사용하는 이유 : 데이터베이스 사용시 커넥션을 생성하는데 대부분의 시간이 소요됨(로컬 테스트 20배). 때문에 커넥션 풀에 이전에 사용한 커넥션을 저장하여 매번 커넥션을 생성하지 않아도 되도록 함
- 커넥션 재사용의 문제 : 커넥션은 DB와 애플리케이션간의 연결을 의미. 한쪽에서 끊거나 네트워크의 문제로 쉽게 끊어짐. 끊어진 커넥션으로 요청을 할 시 timeout 시간동안 해당 요청을 잡고 있어 전체 서비스에 영향을 미칠수 있음
- 끊어진 커넥션 문제를 예방하는 방법
  - pool_recycle=3600: 커넥션의 수명을 명시적으로 설정. 생성 후 1시간이 지난 커넥션은 사용하지 않고 새로 생성한다. 설정시간보다 커넥션이 먼저 죽을 경우 timeout을 완전히 방어하지는 못한다.
  - pool_pre_ping=True: 커넥션을 사용하기 전에 간단한 명령어 (select 1;)을 날려 해당 커넥션이 살아있는지 확인한다. 모든 요청시 해당 명령어를 날린 후 동작하기에 약간의 시간이 더 필요하다.(로컬 테스트 0.01s)



```python
# pool_pre_ping 설정
test_engine = create_async_engine(
  'postgresql+asyncpg://user:password@localhost:5434/testdb',
  echo=True,
  pool_pre_ping=True)

# pool_recycle 설정
test_engine = create_async_engine(
  'postgresql+asyncpg://user:password@localhost:5434/testdb',
  echo=True,
  pool_recycle=1)
```



### Connection 주요 설정

커넥션 풀을 통해 DB와 연결하는 방법에는 여러 필요 설정이 있음

- **최대 풀 크기(Max Pool Size):** 커넥션 풀에서 관리할 수 있는 최대 커넥션 수
- **최소 풀 크기(Min Pool Size):** 커넥션 풀에 항상 유지되어야 하는 최소한의 연결 수
- **커넥션 타임아웃(Connection Timeout):** 클라이언트가 DB측으로 Connection을 요청시 대기하는 최대 시간
- **유휴 커넥션 정리(Idle Connection Test Period):** 정기적으로 유휴 상태의 커넥션을 검사하여 오랜 시간 동안 사용되지 않은 커넥션을 풀에서 제거합니다.
- **커넥션 최대 유휴 시간(Max Idle Time):** 커넥션이 유휴 상태로 남아있을 수 있는 최대 시간입니다. 이 시간이 지나면 커넥션은 자동으로 풀에서 제거됩니다.
- **Max Overflow:** 커넥션 풀의 최대 풀 크기를 초과하여 생성할 수 있는 추가 커넥션의 최대 수를 지정합니다. 
- **Pool Timeout:** 커넥션 풀에서 사용 가능한 커넥션을 얻기 위해 애플리케이션이 기다릴 수 있는 최대 시간



```python
# pool_timeout 설정 
# 10의 커넥션을 poool에 저장하고 11개째의 요청은 1초만에 timeout
test_engine = create_async_engine(
  'postgresql+asyncpg://user:password@localhost:5434/testdb',
  echo=True,
  pool_size=10, 
  max_overflow=0,
  pool_timeout=1)  



# statement_timeout 설정
# 1000ms -> 1s 이상 걸리는 쿼리 요청에 대해 timeout 에러 
test_engine = create_async_engine(
  'postgresql+asyncpg://user:password@localhost:5434/testdb',
  echo=True,
  connect_args={"server_settings": {"statement_timeout": "1000"}}  # 단위가 ms, 보통 15s 정도로 설정함
)	
```





## 2. 세션과 비동기 동작에서 스레드와 테스크

sqlalchemy의 sessionmaker 를 이용하여 세션을 생성, 관리

```python
test_engine = create_async_engine('postgresql+asyncpg://user:password@localhost:5434/testdb', echo=True)
session_factory = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
AsyncScopedSession = scoped_session(session_factory)
```





### 세션의 비동기 처리 

세션은 하나의 coroutine에 의해 처리됨. 요청이 들어온 테스크를 coroutine 큐에 넣어놓고 순차적으로 처리. 처리중 awaite를 만나면 처리중엔 task는 다시 큐의 가장 윗단에 넣어놓고 다음 task를 처리.

위의 과정에서 동일 세션에 대한 task가 비동기 적으로 동시에 처리된다면 에러 발생. 기본적으로 세션은 쓰레드 별로 할당되기 때문. 

이를 위해 세션을 테스크 별 할당으로 전환 하여 사용한다.

```python
async_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
AsyncScopedSession = async_scoped_session(async_session_factory, scopefunc=asyncio.current_task)
```


<img width="439" alt="image" src="https://github.com/pai-jk/sqlalchemy-tutorial/assets/88126382/434dc43a-d3c3-4f7d-9bff-3b5b7969a931">





## 3. orm Entity의  각 상태

### 상태값

1. transient : 객체가 생성되었지만 아직 세션에 추가되지 않은 상태, entity 만 만든 상태

   ```python
   given_user0 = UserEntity(id=None, name="test0")
   ```

   

2. pending : 세션에 추가된 상태, orm에서만 관리하고 있음

   ```python
   session.add(given_user0)
   ```

   

3. persistent : 세션에 추가되어서 관리되는 상태,

   ```python
   session.flush([given_user0])
   ```

   flush : session에 추가된 Entity의 상태(CRUD)에 대한 모든 명령을 DB에 전달한다. 

   

4. expired : 변경이 적용된 Entity에 대한 상태를 보장할 수 없는 상태

   ```python
   session.commit()
   ```

   - commit: flush 통해 전달된 상태를 DB에 적용한다.

   - `expire_on_commit=False `로 설정하면, commit 이후에도 expired = true가 되지않아서 데이터에 대한 접근이 가능함
   - 다만 이 방법은 expire 문제를 야기할수 있음 

5. detached : 세션 아웃

   ```python
   session.refresh(given_user0)
   ```

   



## 4. orm Entity에서 관계형 데이터베이스의 테이블을 가져오는 방법

관계형 테이블을 어떻게 entity로 표현할것인가

```python
@dataclass
class User:
    id: Optional[int]
    name: str
    posts: List['Post']

    @staticmethod
    def new(name: str):
        return User(id=None, name=name, posts=[])

@dataclass
class Post:
    id: Optional[int]
    user_id: str
    title: str

    @staticmethod
    def new(user_id: str, title: str):
        return Post(id=None, user_id=user_id, title=title)
```



### 방법1. 

UserEntity 만 조회. `user_entity.awaitable_attrs.posts` 를 통해 posts가 필요할 때만 다시 조회

- 조회 할때마다만 쿼리가 발생함
- 모두 조회 시 N+1 문제가 발생



단일 

```python
async with test_scoped_session() as session:
  stmt = select(UserEntity)
  result = await session.execute(stmt)
  user_entities = result.scalars().all()
  
  for user_entity in user_entities:
    post_entities = await user_entity.awaitable_attrs.posts

```



### 방법2.

select 시 options을 추가하여 where in , 또는 join 등으로 조회 



#### selectinload 

테이블 마다 한번의 쿼리문이 발생하게 됨, 모든 데이터를 가져옴

```sql
SELECT users.id, users.name FROM users
SELECT posts.user_id AS posts_user_id, posts.id AS posts_id, posts.title AS posts_title FROM posts WHERE posts.user_id IN ($1::INTEGER, $2::INTEGER)
```

```python
async with test_scoped_session() as session:
  stmt = select(UserEntity).options(selectinload(UserEntity.posts))
  result = await session.execute(stmt)
  user_entities = result.scalars().all()

  for user_entity in user_entities:
    post_entities = user_entity.posts
```





#### joininload

join을 통해 한번에 가져옴, 1대N의 경우 중복된 값이 많아져 네트워크 비용이 늘어남. 중복 제거가 필요함

```sql
SELECT users.id, users.name, posts_1.id AS id_1, posts_1.title, posts_1.user_id 
FROM users LEFT OUTER JOIN posts AS posts_1 ON users.id = posts_1.user_id
```

```python
async with test_scoped_session() as session:
  stmt = select(UserEntity).options(joinedload(UserEntity.posts))
  result = await session.execute(stmt)
  user_entities = result.scalars().unique().all() # 중복 제거

  for user_entity in user_entities:
    post_entities = user_entity.posts
```
