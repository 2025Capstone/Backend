from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func
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