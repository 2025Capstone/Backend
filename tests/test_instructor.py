import pytest
from fastapi.testclient import TestClient
from app.main import app

import uuid

client = TestClient(app)

# 테스트용 강의자 정보 (실제 환경에 맞게 수정 필요)
TEST_EMAIL = f"instructor_test_{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "testpassword123!"
TEST_NAME = "테스트강사"

@pytest.fixture(scope="module")
def instructor_tokens():
    # 회원가입 (항상 새로운 이메일로 가입)
    resp = client.post("/api/v1/instructors-auth/register", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME
    })
    assert resp.status_code == 200
    # 로그인
    resp = client.post("/api/v1/instructors-auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert resp.status_code == 200
    tokens = resp.json()
    return tokens

def test_instructor_register_and_login():
    temp_email = f"instructor_test_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/api/v1/instructors-auth/register", json={
        "email": temp_email,
        "password": TEST_PASSWORD,
        "name": TEST_NAME
    })
    assert resp.status_code == 200
    resp = client.post("/api/v1/instructors-auth/login", json={
        "email": temp_email,
        "password": TEST_PASSWORD
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "id" in data
    assert "name" in data
    assert "email" in data

def test_instructor_token_refresh(instructor_tokens):
    refresh_token = instructor_tokens["refresh_token"]
    resp = client.post("/api/v1/instructors-auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data

def test_create_lecture_and_get_lectures(instructor_tokens):
    access_token = instructor_tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    # 강의 생성
    resp = client.post("/api/v1/instructors/lectures", headers=headers, json={"name": "AI캡스톤강의"})
    assert resp.status_code == 200
    lecture_id = resp.json()["id"]
    # 내 강의 목록 조회
    resp = client.get("/api/v1/instructors/lectures", headers=headers)
    assert resp.status_code == 200
    lectures = resp.json()["lectures"]
    assert any(l["id"] == lecture_id for l in lectures)

def test_get_my_lecture_students(instructor_tokens):
    access_token = instructor_tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    # 강의 생성
    resp = client.post("/api/v1/instructors/lectures", headers=headers, json={"name": "학생목록테스트강의"})
    assert resp.status_code == 200
    lecture_id = resp.json()["id"]
    # 수강생 목록 조회
    resp = client.post("/api/v1/instructors/lecture/students", headers=headers, json={"lecture_id": lecture_id})
    assert resp.status_code == 200
    assert "students" in resp.json()

def test_update_lecture_visibility(instructor_tokens):
    access_token = instructor_tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    # 강의 생성
    resp = client.post("/api/v1/instructors/lectures", headers=headers, json={"name": "공개여부테스트강의"})
    assert resp.status_code == 200
    lecture_id = resp.json()["id"]
    # 공개여부 변경
    resp = client.patch("/api/v1/instructors/lectures/visibility", headers=headers, json={"lecture_id": lecture_id, "is_public": True})
    assert resp.status_code == 200
    assert resp.json()["is_public"] is True

