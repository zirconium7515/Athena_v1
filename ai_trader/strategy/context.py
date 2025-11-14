# Athena_v1/ai_trader/strategy/context.py
# [수정] 2024.11.11 - (오류) SyntaxError: invalid syntax (// 주석 수정)
# [수정] 2024.11.11 - (경고) FutureWarning: fillna(method='ffill') -> ffill()
# [수정] 2024.11.14 - (Owl v1) 임시 함수 'check_channel_v3_4' 제거
"""
Strategy v3.5 (Owl - Tactic 1) - 1단계: 컨텍스트 분석
(피벗, 채널 등)
"""
import pandas as pd
import numpy as np

def calculate_pivots(df: pd.DataFrame, left: int, right: int) -> pd.DataFrame:
    """
    v3.5 1-1. 피벗 하이(PH) / 피벗 로우(PL) 계산
    (ZigZag 인디케이터와 유사)
    """
    
    # (임시 구현)
    # TODO: v3.5 기준(좌:10, 우:5)에 맞는 정확한 피벗 계산 로직 구현 필요
    
    # (초간단 임시 피벗: 5일 최고가/최저가)
    window_size = left + right + 1
    df['PH_temp'] = df['high'].rolling(window=window_size).max()
    df['PL_temp'] = df['low'].rolling(window=window_size).min()

    # (간단한 피벗 찾기: window_size 내 최고/최저)
    df['PH'] = df['high'][(df['high'] == df['PH_temp'])].shift(right)
    df['PL'] = df['low'][(df['low'] == df['PL_temp'])].shift(right)
    
    # [수정] (FutureWarning: 'method' is deprecated)
    # (최신 피벗이 NaN이 되는 것을 방지하기 위해 ffill)
    df['PH'] = df['PH'].ffill()
    df['PL'] = df['PL'].ffill()
    # --- (수정 끝) ---
    
    df.drop(columns=['PH_temp', 'PL_temp'], inplace=True)
    
    return df

# [제거] (Owl v1) (v3.5의 임시 채널 함수 제거)
# def check_channel_v3_4(df: pd.DataFrame, current_price: float) -> bool:
#    ...