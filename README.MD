
환경 설정
```bash
python3 -m venv .venv
source .venv/bin/activate
```

라이브러리 설치
```bash
pip install -r requirements.txt
```


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
```bash
alembic upgrade head
```

더미데이터 추가 코드
```bash
mysql -h 127.0.0.1 -P 3306 -u root -p demo < dummy.sql
```
비밀번호는 password123!

학생 테스트 코드
```bash
PYTHONPATH=. pytest tests/test_student.py 
```


instructor 테스트 코드
```bash
PYTHONPATH=. pytest tests/test_instructor.py 
```


# 영상 썸네일 추출을 위해 ffmpeg(시스템 패키지)가 필요합니다.
# macOS: brew install ffmpeg
# Ubuntu: sudo apt-get install ffmpeg