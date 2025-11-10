# Athena_v1/config.py
"""
설정 파일 (환경 변수 로드)
"""
import os
from dotenv import load_dotenv
from functools import lru_cache

@lru_cache()
def get_settings():
    """ 환경 변수 로드 (.env 파일) """
    load_dotenv(dotenv_path=".env")
    
    return {
        "UPBIT_ACCESS_KEY": os.getenv("UPBIT_ACCESS_KEY"),
        "UPBIT_SECRET_KEY": os.getenv("UPBIT_SECRET_KEY"),
        "DB_NAME": "athena_v1_trade_history.db",
        "LOG_FILE": "athena_v1.log",
    }