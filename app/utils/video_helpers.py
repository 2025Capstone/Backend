import tempfile
from moviepy.editor import VideoFileClip
from fastapi import UploadFile
import subprocess
import os
import uuid
from app.core.config import settings

def extract_video_duration(upload_file: UploadFile) -> float:
    """
    업로드된 파일에서 영상 길이를 추출한 후 초 단위 duration 반환.
    업로드 파일의 파일 포인터를 재설정합니다.
    """
    # 임시 파일에 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        contents = upload_file.file.read()
        tmp.write(contents)
        tmp.flush()
    # moviepy로 임시 파일에서 길이 추출
    clip = VideoFileClip(tmp.name)
    duration = clip.duration  # 초 단위 (실수)
    clip.close()
    # 파일 포인터 재설정 (S3 업로드를 위해)
    upload_file.file.seek(0)
    return duration


def convert_to_hls(file_data, file_name: str):
    """MP4 파일을 HLS로 변환하여 고유 폴더 내에 저장하고, 파일 목록과 플레이리스트 경로 반환"""
    # 1. 고유한 폴더 이름 생성
    unique_folder = str(uuid.uuid4())
    hls_dir = os.path.join(tempfile.mkdtemp(), unique_folder)  # 고유 폴더 생성
    os.makedirs(hls_dir, exist_ok=True)

    # 2. 플레이리스트 파일 경로 설정 (고정된 이름 사용)
    playlist_path = os.path.join(hls_dir, "playlist.m3u8")

    # 3. 원본 파일 임시 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(file_data.read())
        tmp.flush()
        temp_file_path = tmp.name

    try:
        # 4. FFmpeg 명령어 실행: -hls_segment_filename로 고정된 패턴 사용, -hls_base_url로 절대 URL 설정
        command = [
            "ffmpeg",
            "-i", temp_file_path,
            "-codec:", "copy",
            "-start_number", "0",
            "-hls_time", "10",
            "-hls_list_size", "0",
            "-hls_segment_filename", os.path.join(hls_dir, "segment%d.ts"),
            "-hls_base_url", f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/hls/{unique_folder}/",
            "-f", "hls",
            playlist_path
        ]
        subprocess.run(command, check=True)
        # 5. 반환: 고유 폴더 내의 모든 파일과 플레이리스트 경로
        hls_files = [os.path.join(hls_dir, f) for f in os.listdir(hls_dir)]
        return hls_files, playlist_path, unique_folder
    finally:
        os.remove(temp_file_path)