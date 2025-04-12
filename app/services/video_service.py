import boto3
from botocore.exceptions import NoCredentialsError
from app.core.config import settings
from uuid import uuid4
from app.utils.video_helpers import convert_to_hls
import os

# S3 클라이언트 생성
s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY,
    aws_secret_access_key=settings.AWS_SECRET_KEY,
    region_name=settings.AWS_REGION
)

def upload_video_to_s3(file_data, file_name: str):
    """비디오 파일을 HLS 변환 후 S3에 업로드하고, 변환된 플레이리스트(.m3u8) URL 반환"""
    try:
        # 1. MP4를 HLS로 변환 (고유 폴더 유지)
        hls_files, playlist_path, unique_folder = convert_to_hls(file_data, file_name)  # ✅ 3개 변수 모두 받음

        # 2. 변환된 HLS 파일들을 S3에 업로드
        hls_s3_urls = []
        for file_path in hls_files:
            with open(file_path, "rb") as f:
                # S3 키: hls/<unique_folder>/<원본 파일 이름>
                s3_file_name = f"hls/{unique_folder}/{os.path.basename(file_path)}"
                content_type = "application/vnd.apple.mpegurl" if file_path.endswith(".m3u8") else "video/MP2T"
                s3_client.upload_fileobj(
                    f,
                    settings.AWS_S3_BUCKET_NAME,
                    s3_file_name,
                    ExtraArgs={"ACL": "public-read", "ContentType": content_type}
                )
                s3_url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_file_name}"
                hls_s3_urls.append(s3_url)

        # 3. 업로드된 플레이리스트(.m3u8) URL 반환 (고유 폴더를 포함하여 저장)
        playlist_s3_url = next((url for url in hls_s3_urls if url.endswith("playlist.m3u8")), None)
        if not playlist_s3_url:
            raise Exception("HLS 변환 후 플레이리스트(.m3u8) 파일이 S3에 업로드되지 않았습니다.")

        return playlist_s3_url, unique_folder  # ✅ 고유 폴더까지 반환 (React에서 활용 가능)

    except NoCredentialsError:
        raise Exception("AWS 자격 증명 오류: credentials 확인 필요")