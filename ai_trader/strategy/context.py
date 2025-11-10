# Athena_v1/ai_trader/strategy/context.py
"""
Strategy v3.5 - 1단계: 컨텍스트 분석
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
    df['PH'] = df['high'].rolling(window=left+right+1, center=True).max()
    df['PL'] = df['low'].rolling(window=left+right+1, center=True).min()
    
    # (최신 피벗이 NaN이 되는 것을 방지하기 위해 ffill)
    df['PH'] = df['PH'].fillna(method='ffill')
    df['PL'] = df['PL'].fillna(method='ffill')
    
    return df

def check_channel_v3_4(df: pd.DataFrame, current_price: float) -> bool:
    """
    v3.5 1-2. 채널 분석 (v3.4 기준)
    (현재가가 가장 최근 채널의 하단 지지선 근처인지 확인)
    """
    
    # (임시 구현)
    # TODO: v3.4 전략 문서에 정의된 '채널 작도' 로직 구현 필요
    
    # (초간단 임시 로직: 최근 20개 캔들 저가(PL) 근처인가?)
    if 'PL' not in df.columns:
        return False
        
    recent_low_pivot = df.iloc[-20:]['PL'].min()
    
    if pd.isna(recent_low_pivot):
        return False
        
    # (현재가가 최근 저가 피벗의 1% 이내에 있는가?)
    if (recent_low_pivot * 0.99) <= current_price <= (recent_low_pivot * 1.01):
        return True
        
    return False