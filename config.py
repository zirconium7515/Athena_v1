# Athena_v1/config.py
# [수정] 2024.11.11 - (오류) ImportError 해결
"""
설정 파일 (main.py에서 사용할 상수들을 정의합니다)
"""
import logging
import os
from dotenv import load_dotenv
from functools import lru_cache

# .env 파일 로드 (UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
# (이 파일의 다른 변수들도 .env에서 읽어올 수 있도록 로드)
load_dotenv(dotenv_path=".env")

# --- main.py (Line 27)에서 임포트하는 상수들 ---

# 1. 로그 파일 경로
LOG_FILE_PATH = os.getenv("LOG_FILE", "athena_v1.log")

# 2. DB 파일 경로
DB_FILE_PATH = os.getenv("DB_NAME", "athena_v1_trade_history.db")

# 3. 로그 레벨
# (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR)
LOG_LEVEL = logging.INFO 

# -----------------------------------------------

# (참고) .env의 API 키는 main.py의 /api/set-keys 엔드포인트를 통해
# 메모리(api_keys_store)로 직접 로드되므로, 봇 실행 로직에서는 사용되지 않습니다.
UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")

# (기존 함수 - 현재 main.py에서는 사용되지 않음)
@lru_cache()
def get_settings():
    """ (참고용) 설정 딕셔너리 반환 함수 """
    return {
        "UPBIT_ACCESS_KEY": UPBIT_ACCESS_KEY,
        "UPBIT_SECRET_KEY": UPBIT_SECRET_KEY,
        "DB_NAME": DB_FILE_PATH,
        "LOG_FILE": LOG_FILE_PATH,
    }