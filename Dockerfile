# Athena_v1/Dockerfile
# [신규] 2024.11.15 - (Docker 배포) 벡엔드 Dockerfile
# --- (Vive Coding) 벡엔드 (FastAPI) 컨테이너 ---

# 1. 기본 이미지 (Python 3.11)
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. (중요) 한글/시간대 설정 (로그가 깨지지 않도록)
ENV LANG=C.UTF-8
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 4. 필수 라이브러리 복사 및 설치
COPY requirements.txt .
# (pandas-ta 컴파일을 위해 build-essential 설치)
RUN apt-get update && apt-get install -y build-essential && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# 5. 프로젝트 소스 코드 복사
COPY . .

# 6. Gunicorn (프로덕션 서버) 실행
# (main:app을 8000번 포트에서 실행)
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000", "main:app"]