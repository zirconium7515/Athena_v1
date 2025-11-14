# Athena_v1/ai_trader/strategy/patterns.py
# [수정] 2024.11.14 - (Owl v1) v3.5(Tactic 1) 호환을 위한 필수 함수 정의
# [수정] 2024.11.14 - (Owl v1) Tactic 3 (Range Bounce Long) 함수 'find_bollinger_bounce_long' 추가
# [수정] 2024.11.15 - (오류) pandas-ta append=True 버그 (RSI 수동 할당 방식으로 변경)
# [수정] 2024.11.15 - (오류) df.ta (확장) 대신 ta.rsi (직접 호출) 방식으로 변경
# [수정] 2024.11.15 - (오류) 'BBL_20_2.0_2.0' 버그 (constants.py에서 공용 설정 로드)
"""
Strategy Owl v1 - 패턴 및 신호 검색 헬퍼
(Tactic 1: v3.5 / Tactic 3: Range)
"""
import pandas as pd
import pandas_ta as ta 
import numpy as np
from typing import Dict, Any, Optional

# [신규] (공용 설정 임포트)
from ai_trader.strategy.constants import (
    RSI_PERIOD, RSI_COL,
    BBANDS_LOW_COL, BBANDS_MID_COL
)

# --- (공통) RSI 계산 헬퍼 ---
def _get_rsi(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    (공용 설정) DataFrame의 복사본('copy')에 RSI를 계산하여 반환합니다.
    """
    if RSI_COL not in df.columns:
        try:
            rsi_series = ta.rsi(df['close'], length=RSI_PERIOD)
            
            if rsi_series is None or rsi_series.empty:
                print(f"[WARN] patterns.py: {RSI_COL} 계산 실패 (데이터 부족?).")
                return None
            df[RSI_COL] = rsi_series
        except Exception as e:
            print(f"[WARN] patterns.py: _get_rsi() 중 오류: {e}")
            return None
    return df

# --- (Tactic 1: Bull Trend) v3.5 헬퍼 ---

def find_bullish_ob(df: pd.DataFrame, current_price: float, lookback: int = 10) -> Optional[Dict[str, float]]:
    """
    [v3.5 계승] Bullish OB (지지 오더블록)를 찾습니다.
    (마지막 음봉 + 강한 양봉 돌파 + 현재가 리테스트)
    """
    df_recent = df.iloc[-lookback:].copy()
    
    is_down_candle = df_recent['close'] < df_recent['open']
    
    for i in range(len(df_recent) - 2, 0, -1):
        if is_down_candle.iloc[i]:
            if not is_down_candle.iloc[i+1]:
                bullish_candle = df_recent.iloc[i+1]
                bearish_candle = df_recent.iloc[i] 
                
                if bullish_candle['close'] > bearish_candle['high']:
                    ob_high = bearish_candle['high']
                    ob_low = bearish_candle['low']
                    ob_height = ob_high - ob_low
                    
                    if current_price >= ob_low and current_price <= ob_high:
                        
                        return {
                            "ob_low": ob_low,
                            "ob_high": ob_high,
                            "ob_height": ob_height
                        }
    
    return None

def find_w_pattern(df: pd.DataFrame, current_price: float, lookback: int = 30) -> Optional[Dict[str, float]]:
    """
    [v3.5 계승] W-패턴(이중 바닥)을 찾습니다.
    """
    df_recent = df.iloc[-lookback:].copy()
    
    df_recent = _get_rsi(df_recent)
    if df_recent is None or RSI_COL not in df_recent.columns:
        return None
        
    rsi = df_recent[RSI_COL]
    current_rsi = rsi.iloc[-1]
    
    oversold_touches = (rsi < 35).sum()
    
    if oversold_touches >= 2 and (current_rsi >= 38 and current_rsi <= 45):
        target_price = df_recent['high'].max()
        
        return {
            "low_1": df_recent['low'].min(),
            "low_2": current_price,
            "target_price": target_price
        }
        
    return None

def find_rsi_divergence(df: pd.DataFrame, lookback: int = 30) -> bool:
    """
    [v3.5 계승] RSI 상승 다이버전스를 찾습니다.
    (가격은 하락(LL)하는데, RSI는 상승(HL)하는 경우)
    """
    df_recent = df.iloc[-lookback:].copy()
    
    df_recent = _get_rsi(df_recent)
    if df_recent is None or RSI_COL not in df_recent.columns or df_recent[RSI_COL].isnull().all():
        return False
        
    try:
        low_idx_1 = df_recent['low'].idxmin()
        temp_df_after_low1 = df_recent.loc[low_idx_1:].iloc[1:]
    except ValueError:
        return False 
    
    if temp_df_after_low1.empty:
        return False
        
    try:
        low_idx_2 = temp_df_after_low1['low'].idxmin()
    except ValueError:
        return False
        
    if pd.isna(low_idx_1) or pd.isna(low_idx_2):
        return False
        
    low_price_1 = df_recent.loc[low_idx_1]['low']
    low_price_2 = df_recent.loc[low_idx_2]['low']
    
    low_rsi_1 = df_recent.loc[low_idx_1][RSI_COL]
    low_rsi_2 = df_recent.loc[low_idx_2][RSI_COL]

    if low_price_2 < low_price_1 and low_rsi_2 > low_rsi_1:
        return True
        
    return False

# --- [신규] (Tactic 3: Range) 헬퍼 ---

def find_bollinger_bounce_long(df: pd.DataFrame, current_price: float) -> Optional[Dict[str, float]]:
    """
    [Owl v1] Tactic 3: 횡보 국면 (Range) 롱 진입 신호를 찾습니다.
    (BB 하단 터치 + RSI 과매도)
    
    :param df: H1 DataFrame (EMA, BBands가 이미 계산되어 있어야 함)
    :param current_price: 현재가
    :return: 롱 진입 신호 (dict) 또는 None
    """
    
    # [수정] (공용 설정 사용)
    bb_low_col = BBANDS_LOW_COL 
    bb_mid_col = BBANDS_MID_COL
    
    try:
        df_copy = df.copy()
        df_copy = _get_rsi(df_copy)
        
        if df_copy is None or bb_low_col not in df_copy.columns or RSI_COL not in df_copy.columns:
            print("[WARN] find_bollinger_bounce_long: BBands 또는 RSI가 df에 없습니다.")
            return None
            
        latest_data = df_copy.iloc[-1]
        
        bb_low = latest_data[bb_low_col]
        bb_mid = latest_data[bb_mid_col]
        rsi = latest_data[RSI_COL]
        
        # (TTactic 3 롱 진입 조건)
        is_touch_bb_low = (current_price <= bb_low * 1.001)
        is_rsi_oversold = (rsi <= 35)
        
        if is_touch_bb_low and is_rsi_oversold:
            
            sl_price = bb_low * 0.995
            tp_price = bb_mid
            
            if (current_price - sl_price) <= 0 or (tp_price - current_price) / (current_price - sl_price) < 1.0:
                return None
            
            return {
                "signal_type": "LONG",
                "sl_price": sl_price,
                "tp_price": tp_price,
                "score": 12, 
                "reason": f"Range Bounce Long (RSI: {rsi:.1f})"
            }
            
    except Exception as e:
        print(f"[ERROR] find_bollinger_bounce_long: {e}")
        return None
        
    return None