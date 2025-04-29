import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# 로그인 토큰
STUDENT_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJadXcyc0I3NnE2WkdUYTR3REdkRVFrNzUyNTUyIiwiZXhwIjoxNzUxOTQ3MTgxfQ.yyRHcRDP7JxBhiUg088ivX1_6L0zrDFwx1QJgU4jGJI"

def get_student_token():
    return STUDENT_ACCESS_TOKEN

def test_get_my_enrolled_lectures():
    """
    내 수강신청 강의 목록 조회 (학생)
    """
    # 실제로는 get_student_token()에서 올바른 access_token을 받아야 함
    access_token = get_student_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/v1/students/lecture", headers=headers)
    assert response.status_code == 200
    # 반환값 구조에 따라 검증
    assert "lectures" in response.json() or response.json() == {}


def test_get_my_profile():
    """
    내 프로필 정보 조회 (학생)
    """
    access_token = get_student_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/v1/students/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    # assert data["email"] == STUDENT_EMAIL


def test_update_my_name():
    """
    학생 이름 변경
    """
    access_token = get_student_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.patch("/api/v1/students/profile/name", headers=headers, json={"name": "테스트학생"})
    assert response.status_code == 200
    assert "name" in response.json()


def test_get_lecture_list():
    """
    강의 목록 조회 (학생)
    """
    access_token = get_student_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/v1/students", headers=headers)
    assert response.status_code == 200
    assert "lectures" in response.json()


def test_enroll_and_cancel_enrollment():
    """
    수강신청 및 수강취소
    """
    access_token = get_student_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    # 강의 목록 조회 후 첫 번째 강의 id로 수강신청 시도
    lectures_resp = client.get("/api/v1/students", headers=headers)
    assert lectures_resp.status_code == 200
    lectures = lectures_resp.json().get("lectures", [])
    if not lectures:
        pytest.skip(f"테스트용 강의가 없습니다. lectures: {lectures}")
    lecture_id = lectures[0].get("id")
    if lecture_id is None:
        pytest.skip(f"lecture에 'id'가 없습니다: {lectures[0]}")
    # 수강신청
    enroll_resp = client.post("/api/v1/students/enrollments", headers=headers, json={"lecture_id": lecture_id})
    assert enroll_resp.status_code in [200, 409]  # 이미 신청했으면 409
    # 수강취소
    cancel_resp = client.request(
        "DELETE",
        "/api/v1/students/enrollments",
        headers=headers,
        json={"lecture_id": lecture_id}
    )
    assert cancel_resp.status_code == 200


def test_get_lecture_video_list():
    """
    특정 강의의 영상 목록 조회
    """
    access_token = get_student_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    # 내 수강신청 강의 목록에서 강의 id 확보
    enrolled_resp = client.get("/api/v1/students/lecture", headers=headers)
    assert enrolled_resp.status_code == 200
    lectures = enrolled_resp.json().get("lectures", [])
    if not lectures:
        pytest.skip(f"수강신청된 강의가 없습니다. lectures: {lectures}")
    lecture_id = lectures[0].get("id")
    if lecture_id is None:
        pytest.skip(f"lecture에 'id'가 없습니다: {lectures[0]}")
    # 영상 목록 조회
    video_resp = client.post("/api/v1/students/lecture/video", headers=headers, json={"lecture_id": lecture_id})
    assert video_resp.status_code == 200
    assert "videos" in video_resp.json()


def test_get_video_s3_link():
    """
    특정 영상의 S3 링크 제공
    """
    access_token = get_student_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    # 내 수강신청 강의 목록에서 강의 id 확보
    enrolled_resp = client.get("/api/v1/students/lecture", headers=headers)
    assert enrolled_resp.status_code == 200
    lectures = enrolled_resp.json().get("lectures", [])
    if not lectures:
        pytest.skip(f"수강신청된 강의가 없습니다. lectures: {lectures}")
    lecture_id = lectures[0].get("id")
    if lecture_id is None:
        pytest.skip(f"lecture에 'id'가 없습니다: {lectures[0]}")
    # 영상 목록 조회
    video_resp = client.post("/api/v1/students/lecture/video", headers=headers, json={"lecture_id": lecture_id})
    assert video_resp.status_code == 200
    videos = video_resp.json().get("videos", [])
    if not videos:
        pytest.skip("해당 강의에 영상이 없습니다.")
    video_id = videos[0].get("id")
    if video_id is None:
        pytest.skip(f"video에 'id'가 없습니다: {videos[0]}")
    # S3 링크 요청
    s3_resp = client.post("/api/v1/students/lecture/video/link", headers=headers, json={"video_id": video_id})
    assert s3_resp.status_code == 200
    assert "s3_link" in s3_resp.json()
