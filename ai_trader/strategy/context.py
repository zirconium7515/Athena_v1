# Athena_v1/ai_trader/strategy/context.py
"""
Strategy v3.5 - 1단계: 컨텍스트 분석
(피벗, 채널, 추세 분석)
"""
import pandas as pd
from .pivot_channel import calculate_pivots, calculate_channel
from .patterns import detect_trend_sma

def analyze_context_v3_5(df_h1: pd.DataFrame) -> dict:
    """
    1단계: 컨텍스트 분석 (H1 캔들 기준)
    :return: (dict) 분석 결과
    """
    
    context = {}

    # 1-1. 피벗 (PH, PL) 계산 (좌:10, 우:5)
    pivots = calculate_pivots(df_h1, left_bars=10, right_bars=5)
    # pivots = {'PH': [...], 'PL': [...]}
    
    # 1-2. 채널 작도 (v3.4 기준)
    channel = calculate_channel(df_h1, pivots)
    # channel = {'type': 'ASC'/'DESC'/'FLAT', 'upper': pd.Series, 'lower': pd.Series}
    
    context['channel_type'] = channel.get('type', 'FLAT')

    # 1-2. (보너스) 현재 가격이 채널 하단 근처인가?
    current_price = df_h1['close'].iloc[-1]
    channel_lower = channel.get('lower')
    if channel_lower is not None and not channel_lower.empty:
        last_lower_val = channel_lower.iloc[-1]
        if pd.notna(last_lower_val) and current_price < (last_lower_val * 1.01): # 하단선 1% 이내
            context['location'] = 'LOW'
        else:
            context['location'] = 'MID' # (HIGH/MID 구분 단순화)
    else:
        context['location'] = 'N/A'
        
    # 1-3. 시장 구조/추세 판단
    # (단순화: 50-SMA 200-SMA)
    trend = detect_trend_sma(df_h1, short_ma=50, long_ma=200) # 'UP' / 'DOWN' / 'FLAT'
    context['trend'] = trend
    
    # 1-4. 최종 컨텍스트 판단 (매수 우위 여부)
    # (조건: 추세가 'UP' 이거나, 채널이 'ASC' 이거나, 채널 하단 'LOW'에 위치)
    is_long_biased = (
        context['trend'] == 'UP' or
        context['channel_type'] == 'ASC' or
        context['location'] == 'LOW'
    )
    context['is_long_biased'] = is_long_biased

    return context