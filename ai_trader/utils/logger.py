# Athena_v1/ai_trader/utils/logger.py
"""
통합 로깅 설정
(파일 출력 및 콘솔 출력)
"""
import logging
import sys

# 이미 설정된 로거를 저장하기 위한 딕셔너리
loggers = {}

def setup_logger(name: str, log_file: str, level=logging.INFO):
    """
    로거를 설정하거나 기존 로거를 반환합니다.
    """
    if name in loggers:
        return loggers[name]

    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 중복 핸들러 방지
    if logger.hasHandlers():
        logger.handlers.clear()

    # 포맷터 생성
    formatter = logging.Formatter(
        '%(asctime)s [%(name)s:%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. 파일 핸들러 (로그 파일)
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"파일 로그 핸들러 설정 실패: {e}")

    # 2. 스트림 핸들러 (콘솔)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 전파(propagate) 방지 (루트 로거로 메시지 전달 X)
    logger.propagate = False

    loggers[name] = logger
    return logger