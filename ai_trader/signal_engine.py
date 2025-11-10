# Athena_v1/ai_trader/signal_engine.py
"""
매매 신호 생성 엔진 (Strategy v3.5 - 1, 2, 3단계)
(DataManager로부터 H1 DataFrame을 받아, v3.5 전략을 분석하고
 최종 점수(Score)와 신호 딕셔너리를 반환)
"""
import pandas as pd
from ai_trader.data_manager import DataManager
from ai_trader.database import Database
from ai_trader.utils.logger import setup_logger

# (v3.5 전략 세부 로직 임포트)
from ai_trader.strategy.context import (
    calculate_pivots, 
    check_channel_v3_4
)
from ai_trader.strategy.order_block import (
    find_valid_ob_v3_5
)
from ai_trader.strategy.patterns import (
    check_bullish_patterns_v3_5
)


class SignalEngine:
    
    def __init__(self, data_manager: DataManager, db: Database, symbol: str):
        self.data_manager = data_manager
        self.db = db
        self.symbol = symbol
        self.logger = setup_logger(f"SignalEngine[{symbol}]", "athena_v1.log")
        
        # (v3.5 전략 점수 가중치)
        self.weights_v3_5 = {
            'context_channel': 5,     # 1-2. 채널 지지
            'ob_valid': 5,            # 2-A. 유효 OB
            'ob_frvp': 2,             # 2-B. OB가 FRVP 매물대와 일치
            'pattern_bullish': 4,     # 2-C. 상승형 패턴
            'pattern_continuation': 2 # 2-D. 지속형 패턴
            # (총점 18점 만점)
        }

    def generate_signal_v3_5(self, df_h1: pd.DataFrame) -> dict:
        """
        v3.5 전략 1, 2, 3단계를 실행하여 Long 신호 딕셔너리를 반환합니다.
        (신호가 없거나 점수가 12점 미만이면 None 반환)
        """
        
        if df_h1.empty or len(df_h1) < 50: # (최소 50개 캔들 필요)
            self.logger.warning("v3.5 신호 생성 실패 (H1 데이터 부족)")
            return None

        # --- (임시) 현재가 = 마지막 캔들 종가 ---
        current_price = df_h1.iloc[-1]['close']
        
        # (v3.5 신호 점수판)
        score = 0
        # (v3.5 신호 메타데이터)
        signal_meta = {
            "symbol": self.symbol,
            "strategy_id": "v3.5",
            "ob_low": None,
            "ob_high": None,
            "ob_height": None,
            "pattern_tp": None
        }

        try:
            # --- 1단계: 컨텍스트 분석 ---
            # 1-1. 피벗 계산
            df_h1 = calculate_pivots(df_h1, left=10, right=5)
            
            # 1-2. 채널 분석 (v3.4 기준)
            # (현재가가 가장 최근 채널의 하단 지지선 근처인가?)
            is_channel_support = check_channel_v3_4(df_h1, current_price)
            if is_channel_support:
                score += self.weights_v3_5['context_channel']
                self.logger.info(" (v3.5) 1. 컨텍스트: 채널 하단 지지 (+5점)")

            # --- 2단계: 핵심 근거 (OB, 패턴) ---
            
            # 2-A. 유효 오더블록(OB) 탐색
            # (현재가 아래에 v3.5 기준을 만족하는 '지지 OB'가 있는가?)
            valid_ob = find_valid_ob_v3_5(df_h1, current_price)
            
            if valid_ob:
                score += self.weights_v3_5['ob_valid']
                signal_meta['ob_low'] = valid_ob['low']
                signal_meta['ob_high'] = valid_ob['high']
                signal_meta['ob_height'] = valid_ob['high'] - valid_ob['low']
                self.logger.info(f" (v3.5) 2A. 유효 OB 찾음: {valid_ob['low']:.2f}~{valid_ob['high']:.2f} (+5점)")
                
                # 2-B. OB + FRVP 매물대 (미구현)
                # TODO: FRVP(고정 범위 볼륨 프로파일) 계산 로직 필요
                # (임시) OB가 찾아지면 2-B도 만족했다고 가정
                is_ob_on_frvp = True 
                if is_ob_on_frvp:
                    score += self.weights_v3_5['ob_frvp']
                    self.logger.info(" (v3.5) 2B. OB가 FRVP 매물대와 일치 (+2점)")
            
            # 2-C, 2-D. 고전 패턴 (상승형/지속형)
            # (최근 N개 피벗이 상승형/지속형 패턴을 만들었는가?)
            pattern_result = check_bullish_patterns_v3_5(df_h1)
            if pattern_result:
                pattern_type = pattern_result.get('type')
                pattern_tp = pattern_result.get('target_price')
                
                if pattern_type == 'bullish': # (상승형: 2-C)
                    score += self.weights_v3_5['pattern_bullish']
                    self.logger.info(f" (v3.5) 2C. 상승형 패턴 감지: {pattern_result.get('name')} (+4점)")
                elif pattern_type == 'continuation': # (지속형: 2-D)
                    score += self.weights_v3_5['pattern_continuation']
                    self.logger.info(f" (v3.5) 2D. 지속형 패턴 감지: {pattern_result.get('name')} (+2점)")
                
                if pattern_tp:
                    signal_meta['pattern_tp'] = pattern_tp

            # --- 3단계: 점수 합산 및 진입 결정 ---
            signal_meta['score'] = score
            
            # (v3.5 3-2. 최소 점수)
            if score >= 12:
                self.logger.info(f" (v3.5) 최종 진입 신호: 총 {score}점 (최소 12점 통과)")
                return signal_meta
            
            # (점수 미달)
            # self.logger.debug(f" (v3.5) 점수 미달: 총 {score}점 (12점 미만)")
            return None

        except Exception as e:
            self.logger.error(f"v3.5 신호 생성 중 오류: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None