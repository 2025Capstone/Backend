라이브러리 설치
```bash
pip install -r requirements.txt
```
ㅇ

데이터베이스 테이블 자동 생성

```bash
uvicorn app.main:app --reload
```

데이터베이스 버전 생성
```bash
alembic revision --autogenerate -m "test" 
```
데이터베이스 테이블 생성
```bash
alembic upgrade head
```