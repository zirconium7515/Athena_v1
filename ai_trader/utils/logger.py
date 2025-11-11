# Athena_v1/ai_trader/utils/logger.py
# [수정] 2024.11.11 - (오류) SyntaxError: invalid syntax (// 주석 수정)
"""
로깅(Logging) 설정 유틸리티
"""
import logging
import sys
from logging.handlers import RotatingFileHandler

# (중복 로거 생성을 방지하기 위한 딕셔너리)
loggers = {}

def setup_logger(name: str, log_file: str, level=logging.INFO):
    """
    이름(name)과 로그 파일(log_file)을 기반으로 로거를 설정합니다.
    이미 설정된 이름의 로거는 기존 객체를 반환합니다 (중복 방지).
    """
    
    global loggers
    
    # (이미 생성된 로거가 있으면 반환)
    if loggers.get(name):
        return loggers.get(name)

    # --- 새 로거 생성 ---
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False # (상위 로거로 전파 방지)

    # --- 포맷터 (Formatter) ---
    # (예: [2024-11-11 02:52:43] [INFO] [MainApp] - 메시지)
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- 핸들러 (Handler) 1: 파일 출력 ---
    # (RotatingFileHandler: 파일 크기가 5MB 넘으면 새 파일, 최대 5개 유지)
    try:
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=5*1024*1024, # 5MB
            backupCount=5,
            encoding='utf-8' # (UTF-8 인코딩 추가)
        )
        file_handler.setFormatter(formatter)
        
        # (로거에 핸들러 추가 - 중복 추가 방지)
        if not logger.handlers:
            logger.addHandler(file_handler)
            
            # --- 핸들러 (Handler) 2: 콘솔(터미널) 출력 ---
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    except PermissionError:
        # (여러 프로세스에서 동시에 로거에 접근하려 할 때 발생 가능)
        print(f"경고: 로그 파일 '{log_file}'에 대한 접근 권한이 없습니다. 파일 핸들러를 건너뜁니다.")
        # (콘솔 핸들러만이라도 추가)
        if not logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
    except Exception as e:
        print(f"로거 설정 중 예외 발생: {e}")
        if not logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)


    # (생성된 로거를 딕셔너리에 저장)
    loggers[name] = logger
    return logger