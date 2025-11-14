# Athena_v1/ai_trader/strategy/regime.py
# [신규] 2024.11.14 - (Owl v1) Phase 1: 시장 국면 분석
# [수정] 2024.11.15 - (오류) [FATAL] KeyError: 'BBB_20_2.0' (밴드폭 수동 계산)
# [수정] 2024.11.15 - (오류) [FATAL] KeyError: 'BBU_20_2.0' (컬럼 생성 확인 방어 코드 추가)
# [수정] 2024.11.15 - (오류) BBands 생성 실패 (NaN 결측치 ffill/dropna 처리 추가)
# [수정] 2024.11.15 - (오류) pandas-ta append=True 버그 (수동 할당 방식으로 변경)
# [수정] 2024.11.15 - (오류) pandas-ta가 BBands 컬럼을 반환하지 않는 버그 (최종 방어)
# [수정] 2024.11.15 - (오류) df.ta (확장) 대신 ta.ema/ta.bbands (직접 호출) 방식으로 변경
# [수정] 2024.11.15 - (오류) BBands 컬럼 반환 실패 (강화된 디버깅 로그 추가)
# [수정] 2024.11.15 - (오류) 'BBL_20_2.0_2.0' 버그 (constants.py에서 STD=2(int) 로드)
"""
Strategy Owl v1 - Phase 1: 시장 국면 분석 (Market Regime Analysis)
"""
import pandas as pd
import pandas_ta as ta 
from typing import Literal

# [신규] (공용 설정 임포트)
from ai_trader.strategy.constants import (
    RSI_PERIOD, BBANDS_PERIOD, BBANDS_STD,
    BBANDS_LOW_COL, BBANDS_MID_COL, BBANDS_UPPER_COL,
    BBANDS_BANDWIDTH_COL, BBANDS_PERCENT_COL,
    EXPECTED_BBANDS_COLS
)

MarketRegime = Literal["BULL", "BEAR", "RANGE"]

# --- EMA 설정 ---
REGIME_EMA_PERIOD = 50 

def analyze_regime(df: pd.DataFrame) -> MarketRegime:
    """
    H1 DataFrame을 받아, 현재 시장 국면(BULL, BEAR, RANGE)을 반환합니다.
    """
    
    if df.empty:
        return "RANGE"
        
    try:
        # --- (오류 방어) 데이터 청소 (NaN 값 처리) ---
        if df.isnull().values.any():
            df.ffill(inplace=True) 
            df.dropna(inplace=True) 
        
        if len(df) < REGIME_EMA_PERIOD:
            return "RANGE" 
        
        # --- 1. 지표 계산 ---
        
        ema_col = f'EMA_{REGIME_EMA_PERIOD}'
        
        # (1-1. EMA 계산)
        ema_series = ta.ema(df['close'], length=REGIME_EMA_PERIOD)
        # (1-2. BBands 계산) (BBANDS_STD = 2 (int) 사용)
        bbands_df = ta.bbands(df['close'], length=BBANDS_PERIOD, std=BBANDS_STD)
        
        # --- (방어 코드) ---
        if ema_series is None or bbands_df is None or bbands_df.empty:
            print(f"[FATAL] 'analyze_regime': EMA 또는 BBands 계산 실패 (NaN/데이터 부족?).")
            return "RANGE"
        
        if not all(col in bbands_df.columns for col in EXPECTED_BBANDS_COLS):
            print(f"[FATAL] 'analyze_regime': ta.bbands()가 BBands 컬럼을 반환하지 않았습니다.")
            print(f"  > 예상 컬럼 (Expected): {EXPECTED_BBANDS_COLS}")
            print(f"  > 실제 반환 (Actual): {list(bbands_df.columns)}")
            return "RANGE"
        # --- (방어 코드 끝) ---

        # (1-3. 수동으로 DataFrame에 합치기)
        df[ema_col] = ema_series
        df[BBANDS_LOW_COL] = bbands_df[BBANDS_LOW_COL]
        df[BBANDS_MID_COL] = bbands_df[BBANDS_MID_COL]
        df[BBANDS_UPPER_COL] = bbands_df[BBANDS_UPPER_COL]
        df[BBANDS_BANDWIDTH_COL] = bbands_df[BBANDS_BANDWIDTH_COL]

        ema_slope = df[ema_col].diff().iloc[-1]
        
        bb_bandwidth = df[BBANDS_BANDWIDTH_COL].iloc[-1]
        
        # --- 2. 변수 준비 ---
        
        current_price = df['close'].iloc[-1]
        ema_50 = df[ema_col].iloc[-1]
        
        if pd.isna(bb_bandwidth) or pd.isna(ema_50) or pd.isna(ema_slope):
             print(f"[WARN] 'analyze_regime': 지표 계산 결과가 NaN입니다. (데이터 {len(df)}개)")
             return "RANGE"
        
        is_squeeze = bb_bandwidth < 5.0
        
        # --- 3. 국면 판독 (Regime Analysis) ---
        
        if is_squeeze or (abs(ema_slope / ema_50) < 0.0001): # (기울기가 0.01% 미만)
            return "RANGE"
            
        if current_price > ema_50 and ema_slope > 0:
            return "BULL"
            
        if current_price < ema_50 and ema_slope < 0:
            return "BEAR"
            
        return "RANGE"

    except KeyError as ke:
        print(f"[FATAL] 'analyze_regime' (KeyError): {ke}. (데이터가 {len(df)}개뿐일 수 있습니다.)")
        return "RANGE"
    except Exception as e:
        print(f"[FATAL] 'analyze_regime' (Unknown Error): {e}")
        return "RANGE"