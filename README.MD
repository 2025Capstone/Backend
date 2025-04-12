라이브러리 설치
```bash
pip install -r requirements.txt
```
ㅇ

FastAPI 서버 실행
```bash
uvicorn app.main:app --reload
```

## 데이터베이스 수정
db/base.py를 수정해야함

데이터베이스 마이그레이션
```bash
alembic revision --autogenerate -m "test" 
```

마이그레이션 파일 수정
```python
```bash
alembic upgrade head
```