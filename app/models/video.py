from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Video(Base):
    __tablename__ = "video"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lecture.id"), nullable=False)
    title = Column(String(255), nullable=False)
    s3_link = Column(String(1023), nullable=False)  # AWS S3 링크
    duration = Column(Integer, nullable=False)  # 초 단위 길이
    upload_at = Column(TIMESTAMP, server_default=func.now())
    index = Column(Integer, nullable=False)  # 영상 순서
    is_public = Column(Integer, nullable=False, default=1)  # 영상 공개 여부(1=공개, 0=비공개)
    video_image_url = Column(String(1023), nullable=True)  # 영상 대표 이미지 URL

    # Lecture 모델과의 관계 추가
    lecture = relationship("Lecture", backref="videos")

class VideoWatchHistory(Base):
    __tablename__ = "video_watch_history"

    id = Column(Integer, primary_key=True, index=True)
    student_uid = Column(String(128), ForeignKey("student.uid"), nullable=False, index=True)
    video_id = Column(Integer, ForeignKey("video.id"), nullable=False, index=True)
    watched_percent = Column(Integer, nullable=False, default=0)  # 0~100
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())