# Athena_v1/ai_trader/signal_engine.py
"""
매매 신호 생성 엔진 (Strategy v3.5)
DataManager로부터 H1 (1시간봉) 데이터를 받아 Strategy v3.5의 
1단계(컨텍스트), 2단계(진입 근거), 3단계(신호 품질)를 분석하여
최종 진입 신호(dict)를 생성합니다.
"""
import pandas as pd
from ai_trader.data_manager import DataManager
from ai_trader.database import Database
from ai_trader.utils.logger import setup_logger

# Strategy v3.5 모듈 임포트
from ai_trader.strategy.context import analyze_context_v3_5
from ai_trader.strategy.order_block import find_valid_ob_v3_5
from ai_trader.strategy.patterns import analyze_patterns_v3_5

class SignalEngine:
    
    def __init__(self, data_manager: DataManager, db: Database, symbol: str):
        self.data_manager = data_manager
        self.db = db
        self.symbol = symbol
        self.logger = setup_logger(f"SignalEngine[{symbol}]", "athena_v1.log")

    def generate_signal_v3_5(self, df_h1: pd.DataFrame) -> dict:
        """
        Strategy v3.5 로직을 실행하여 롱(Long) 신호를 반환합니다.
        신호가 없으면 None을 반환합니다.
        
        :param df_h1: 1시간봉 (H1) DataFrame
        :return: 신호 (dict) 또는 None
        """
        
        if df_h1.empty or len(df_h1) < 50: # 최소 데이터 수 (예: 50개)
            self.logger.warning("데이터가 부족하여 신호 생성을 건너뜁니다.")
            return None

        try:
            # --- 1단계: 컨텍스트 분석 (Context Analysis) ---
            # (피벗, 채널, 추세 분석)
            context = analyze_context_v3_5(df_h1)
            # context = {'trend': 'UP', 'channel': 'ASC', 'location': 'LOW', ...}
            
            # (필터) 1-4. 컨텍스트가 '매수 우위'가 아니면 진입 안 함
            if not context.get('is_long_biased', False):
                self.logger.debug(f"컨텍스트 매수 우위 아님 (Trend: {context.get('trend')})")
                return None

            # --- 2단계: 진입 근거 확보 (Entry Point) ---
            # (OB, 매물대, 피보나치, 패턴)
            
            # 2-A: 유효한 지지 오더블록(OB) 탐색
            # (가장 최근 캔들 기준)
            valid_ob = find_valid_ob_v3_5(df_h1, context)
            
            # (필터) 2-B: 유효 OB가 없으면 진입 안 함
            if valid_ob is None:
                self.logger.debug("유효한 지지 오더블록(OB)을 찾지 못함.")
                return None
            
            # 2-C, 2-D: 기타 패턴 (상승 이탈, 되돌림) 분석
            patterns = analyze_patterns_v3_5(df_h1, valid_ob, context)
            
            
            # --- 3단계: 신호 품질 평가 (Scoring) ---
            # (전략 문서의 점수표 기준)
            score = 0
            reasons = []

            # (1단계 점수)
            if context['trend'] == 'UP': score += 2 # 1-3
            if context['location'] == 'LOW': score += 2 # 1-2 (채널 하단)
            
            # (2단계 점수)
            if valid_ob['is_strong']: score += 3 # 2-B (강한 OB)
            if valid_ob['frvp_support']: score += 3 # 2-B (매물대 지지)
            if valid_ob['fib_support'] == 0.618: score += 3 # 2-B (0.618 되돌림)
            elif valid_ob['fib_support'] == 0.5: score += 2 # 2-B (0.5 되돌림)

            if patterns['is_breakout']: score += 2 # 2-C (추세선/채널 상단 돌파)
            if patterns['is_classic_pattern']: score += 3 # 2-D (고전 패턴)

            # 3-2. 점수 합산 및 최종 결정
            self.logger.info(f"신호 품질 평가 점수: {score}점")

            # (필터) 3-2. 12점 미만은 진입 안 함
            if score < 12:
                self.logger.info(f"점수 미달 ({score}점) - 진입 취소")
                return None

            # --- 최종 신호 생성 (RiskManager에게 전달) ---
            self.logger.info(f"!!! [{self.symbol}] 롱(LONG) 신호 발생 (점수: {score}점) !!!")
            
            signal_data = {
                "symbol": self.symbol,
                "score": score,
                "reason": ", ".join(reasons),
                
                # RiskManager가 SL 및 규모 계산에 사용할 정보
                "ob_low": valid_ob['low'],
                "ob_high": valid_ob['high'],
                "ob_height": valid_ob['high'] - valid_ob['low'],
                
                # (기타 참고 정보)
                "context_trend": context['trend'],
            }
            
            return signal_data

        except Exception as e:
            self.logger.error(f"Strategy v3.5 신호 생성 중 오류: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None