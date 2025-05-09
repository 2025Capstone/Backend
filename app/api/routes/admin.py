from fastapi import APIRouter, Depends,  Body
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.schemas.instructor_auth import  InstructorCreateResponse
from app.services.instructor_service import approve_instructor_by_id
from app.services.admin_service import create_lecture_by_admin, bulk_enroll_students_admin, bulk_unenroll_students_admin, get_all_lectures_with_instructor_name
from app.dependencies.admin_auth import  get_current_admin_token
from app.schemas.instructor import AdminLectureCreate, LectureCreateResponse, BulkEnrollRequest, BulkEnrollResponse, BulkUnenrollRequest, BulkUnenrollResponse
from app.schemas.lecture import LectureListResponse, LectureBase
from app.services.instructor import get_unapproved_instructors
from app.services.auth_service import get_all_instructors, get_all_students
router = APIRouter(
    dependencies=[Depends(get_current_admin_token)]
)


@router.post("/approve-instructor/{instructor_id}", summary="교수자 승인", response_model=InstructorCreateResponse)
def approve_instructor(
    instructor_id: int,
    db: Session = Depends(get_db)
):
    """
    교수자 승인 (관리자 권한 필요)
    """
    result = approve_instructor_by_id(db, instructor_id)
    return InstructorCreateResponse(
        id=result["id"],
        name=result["name"],
        email=result["email"],
        message=result["message"]
    )


@router.post("/lectures", response_model=LectureCreateResponse, summary="강의 생성 (관리자)")
def create_lecture_by_admin_api(
    lecture_in: AdminLectureCreate = Body(...),
    db: Session = Depends(get_db)
):
    """
    관리자가 강의명, 시간표, 강의실, 강의자(instructor_id)까지 지정하여 강의를 생성합니다.
    """
    return create_lecture_by_admin(db, lecture_in)


@router.post("/lecture/enroll", response_model=BulkEnrollResponse, summary="여러 학생 일괄 수강신청 (관리자)")
def admin_bulk_enroll_students_api(
    req: BulkEnrollRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    관리자가 여러 학생을 한 번에 수강신청시킴 (이미 수강신청된 학생은 건너뜀)
    """
    result = bulk_enroll_students_admin(db, req.lecture_id, req.student_uid_list)
    return BulkEnrollResponse(**result)

@router.post("/lecture/unenroll", response_model=BulkUnenrollResponse, summary="여러 학생 일괄 수강취소 (관리자)")
def admin_bulk_unenroll_students_api(
    req: BulkUnenrollRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    관리자가 여러 학생을 한 번에 수강취소시킴 (이미 수강신청 안된 학생은 건너뜀)
    """
    result = bulk_unenroll_students_admin(db, req.lecture_id, req.student_uid_list)
    return BulkUnenrollResponse(**result)


@router.get("/instructors", summary="모든 강의자 정보 조회(관리자)")
def get_all_instructors_api(db: Session = Depends(get_db)):
    """
    DB에 등록된 모든 강의자 정보를 반환합니다.
    비밀번호(password)는 제외합니다.
    """
    instructors = get_all_instructors(db)
    return {"instructors": [
        {k: v for k, v in i.__dict__.items() if k != "password" and not k.startswith("_sa_instance_state")}
        for i in instructors
    ]}


@router.get("/instructors/unapproved", summary="미승인 강의자 리스트 조회(관리자)")
def get_unapproved_instructors_api(db: Session = Depends(get_db)):
    """
    아직 승인되지 않은(관리자 승인 대기중) 강의자 리스트를 반환합니다.
    비밀번호(password)는 제외합니다.
    """
    instructors = get_unapproved_instructors(db)
    return {"instructors": [
        {k: v for k, v in i.__dict__.items() if k != "password" and not k.startswith("_sa_instance_state")}
        for i in instructors
    ]}


@router.get("/students", summary="모든 학생 정보 조회(관리자)")
def get_all_students_api(db: Session = Depends(get_db)):
    """
    DB에 등록된 모든 학생 정보를 반환합니다.
    """
    students = get_all_students(db)
    return {"students": [s.__dict__ for s in students]}


@router.get("/lectures/all", response_model=LectureListResponse, summary="모든 강의 정보 조회(관리자)")
def get_all_lectures_api(db: Session = Depends(get_db)):
    """
    현재 개설되어있는 모든 강의의 id, 강의 이름, 강의자 이름을 반환합니다.
    """
    lectures = get_all_lectures_with_instructor_name(db)
    return {"lectures": lectures}
