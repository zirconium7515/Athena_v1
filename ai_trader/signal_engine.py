# Athena_v1/ai_trader/signal_engine.py
# [수정] 2024.11.11 - (오류) SyntaxError: invalid syntax (// 주석 수정)
# [수정] 2024.11.14 - (Owl v1) SignalEngineV3_5 -> SignalEngineOwlV1로 리팩토링
# [수정] 2024.11.14 - (Owl v1) Phase 1: analyze_regime (국면 분석) 로직 추가
# [수정] 2024.11.14 - (오류) ImportError: cannot import name 'find_bullish_ob_v3_5' (오타 수정)
# [수정] 2024.11.14 - (Owl v1) Tactic 3 (Range Bounce) 구현
# [수정] 2024.11.14 - (Owl v1) RiskManager 리팩토링 (SL/TP를 SignalEngine에서 계산)
"""
Strategy Owl v1 - Phase 2: 국면별 진입 신호 분석 (Tactical Signal Analysis)

'Owl' 전략의 핵심 엔진.
Phase 1(Regime)의 분석 결과를 받아, 3가지 전술(Bull, Bear, Range) 중
하나를 선택하여 진입 신호(dict)를 생성합니다.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

# [신규] (Owl v1) Phase 1 국면 분석기 임포트
from ai_trader.strategy.regime import analyze_regime, MarketRegime
# (v3.5 레거시 임포트)
from ai_trader.strategy.context import calculate_pivots
from ai_trader.strategy.patterns import (
    find_bullish_ob, 
    find_w_pattern, 
    find_rsi_divergence,
    find_bollinger_bounce_long # [신규] (Tactic 3)
)
from ai_trader.utils.logger import setup_logger

class SignalEngineOwlV1:

    def __init__(self):
        self.logger = setup_logger("SignalEngineOwlV1", "athena_v1.log")
        self.logger.info("--- Strategy Owl v1 (Signal Engine) 초기화 ---")

    def generate_signal_owl(self, df_h1: pd.DataFrame, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Owl v1 전략의 메인 진입점 (Phase 1 -> Phase 2)
        
        1. (Phase 1) H1 차트를 분석하여 현재 시장 국면(Regime)을 판독합니다.
        2. (Phase 2) 국면에 맞는 전술(Tactic)을 실행하여 신호를 생성합니다.
        """
        
        # --- Phase 1: 시장 국면 분석 ---
        current_regime = analyze_regime(df_h1)
        
        signal_data: Optional[Dict[str, Any]] = None

        # --- Phase 2: 국면별 전술 실행 ---
        match current_regime:
            
            # --- Tactic 1: 상승 추세 (Bull Trend) ---
            case "BULL":
                self.logger.debug(f"[{symbol}] 국면 판독: BULL. (v3.5 Long 전술 실행)")
                signal_data = self._tactic_bull_trend_v3_5(df_h1, symbol)
            
            # --- Tactic 2: 하락 추세 (Bear Trend) ---
            case "BEAR":
                self.logger.debug(f"[{symbol}] 국면 판독: BEAR. (Short 전술 실행)")
                signal_data = self._tactic_bear_trend(df_h1, symbol)
                
            # --- Tactic 3: 횡보 국면 (Ranging) ---
            case "RANGE":
                self.logger.debug(f"[{symbol}] 국면 판독: RANGE. (Range Bounce 전술 실행)")
                signal_data = self._tactic_range_bounce(df_h1, symbol)

        if signal_data:
            self.logger.info(f"[{symbol}] *** 신규 {signal_data.get('signal_type')} 신호 감지 (국면: {current_regime}) ***")
            
            # [신규] (RiskManager에게 국면/전술 전달)
            signal_data['regime'] = current_regime
            signal_data['tactic'] = signal_data.get('reason', 'Unknown Tactic')
            
            return signal_data
            
        return None

    # --- Tactic 1: 상승 추세 (v3.5) ---
    def _tactic_bull_trend_v3_5(self, df: pd.DataFrame, symbol: str) -> Optional[Dict[str, Any]]:
        """
        [v3.5 계승] Tactic 1: Bullish OB (지지 오더블록) 기반 롱 진입
        """
        try:
            current_price = df.iloc[-1]['close']
            
            # --- 1. 컨텍스트 분석 (v3.5) ---
            df = calculate_pivots(df, left=10, right=5)
            
            # --- 2. 신호 분석 (v3.5) ---
            
            # 2-1. (필수) 지지 오더블록 (Bullish OB)
            ob_signal = find_bullish_ob(df, current_price)
            if not ob_signal:
                return None
            
            score = 10 
            reason = f"Bullish OB ({ob_signal['ob_low']:.2f})"
            
            # 2-2. (가산) W-패턴 (이중 바닥)
            w_pattern = find_w_pattern(df, current_price)
            if w_pattern:
                score += 4
                reason += " + W-Pattern"
                
            # 2-3. (가산) RSI 상승 다이버전스
            rsi_div = find_rsi_divergence(df, lookback=30)
            if rsi_div:
                score += 4
                reason += " + RSI Div"

            # --- 3. 진입 결정 (v3.5) ---
            if score < 12:
                return None
                
            # --- [신규] (Owl v1) SL/TP 계산 (RiskManager 리팩토링) ---
            sl_price = ob_signal['ob_low'] - (ob_signal['ob_height'] * 0.2)
            
            if w_pattern and w_pattern.get('target_price'):
                tp_price = w_pattern['target_price']
            else:
                # (R:R = 2.0)
                risk_per_coin = current_price - sl_price
                tp_price = current_price + (risk_per_coin * 2.0)
            
            if sl_price >= current_price or tp_price <= current_price:
                self.logger.warning(f"[{symbol}] v3.5 SL/TP 계산 오류 (SL: {sl_price}, TP: {tp_price}, 현재가: {current_price})")
                return None

            # --- 4. 리스크 계산용 데이터 반환 ---
            signal_data = {
                "symbol": symbol,
                "signal_type": "LONG",
                "score": score,
                "reason": reason,
                
                # (RiskManager가 사용할 SL/TP)
                "sl_price": sl_price,
                "tp_price": tp_price
            }
            return signal_data
            
        except Exception as e:
            self.logger.error(f"[{symbol}] _tactic_bull_trend_v3_5 실행 중 오류: {e}", exc_info=True)
            return None

    # --- Tactic 2: 하락 추세 (Short) ---
    def _tactic_bear_trend(self, df: pd.DataFrame, symbol: str) -> Optional[Dict[str, Any]]:
        """
        [신규] Tactic 2: Bearish OB (저항 오더블록) 기반 숏 진입
        (TODO: 'Owl v1 - 4단계'에서 구현 예정)
        """
        # (현재는 구현되지 않았으므로 항상 None 반환)
        return None

    # --- Tactic 3: 횡보 국면 (Range) ---
    def _tactic_range_bounce(self, df: pd.DataFrame, symbol: str) -> Optional[Dict[str, Any]]:
        """
        [신규] Tactic 3: Bollinger Bounce (볼린저 밴드) 기반 평균 회귀
        """
        try:
            current_price = df.iloc[-1]['close']
            
            # (df에는 analyze_regime에서 계산한 BBANDS, RSI 지표가 이미 포함되어 있음)
            
            # 1. 롱(Long) 신호 확인
            long_signal = find_bollinger_bounce_long(df, current_price)
            
            if long_signal:
                signal_data = {
                    "symbol": symbol,
                    "signal_type": "LONG",
                    "score": long_signal['score'],
                    "reason": long_signal['reason'],
                    "sl_price": long_signal['sl_price'],
                    "tp_price": long_signal['tp_price']
                }
                return signal_data
                
            # 2. 숏(Short) 신호 확인
            # (TODO: 'Owl v1 - 4단계'에서 find_bollinger_bounce_short 구현)

        except Exception as e:
            self.logger.error(f"[{symbol}] _tactic_range_bounce 실행 중 오류: {e}", exc_info=True)
            return None
            
        return None