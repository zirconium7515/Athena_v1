# Athena_v1/ai_trader/risk_manager.py
# [수정] 2024.11.11 - (오류) SyntaxError: invalid syntax (// 주석 수정)
# [수정] 2024.11.11 - (오류) InsufficientFundsBid (수수료) 문제 해결 (99.9% 버퍼)
# [수정] 2024.11.14 - (Owl v1) ImportError: cannot import name 'SignalV3_5' (SignalOwlV1로 변경)
# [수정] 2024.11.14 - (Owl v1) 리팩토링 (SL/TP를 SignalEngine에서 수신)
# [수정] 2024.11.14 - (Owl v1) Phase 3 (동적 리스크 관리) 로직 구현
"""
Strategy Owl v1 - Phase 3: 동적 리스크 및 포지션 규모 계산

SignalEngine(Phase 2)의 신호(dict)를 받아,
Phase 3(동적 리스크)를 적용하여 최종 포지션 규모(SignalOwlV1)를 계산합니다.
"""
from ai_trader.utils.logger import setup_logger
from ai_trader.data_models import SignalOwlV1, MarketRegime
from typing import Dict, Any, Optional
import math
from datetime import datetime

class RiskManager:
    
    UPBIT_FEE_BUFFER = 0.001 # (0.1%)
    
    def __init__(self, 
                 total_capital: float, 
                 base_risk_per_trade_pct: float = 0.5):
        
        self.logger = setup_logger("RiskManager", "athena_v1.log")
        
        self.total_capital = total_capital
        self.base_risk_per_trade_pct = base_risk_per_trade_pct
        
        # 기본 손실 확정 금액 (예: 1,000,000 * 0.5% = 5,000 KRW)
        self.base_risk_amount = self.total_capital * (self.base_risk_per_trade_pct / 100.0)
        
        self.logger.info(f"RiskManager 초기화: 총 자본금 {total_capital:,.0f} KRW, 기본 리스크 {self.base_risk_amount:,.0f} KRW ({base_risk_per_trade_pct}%)")

    # [수정] (Owl v1) (SL/TP를 SignalEngine으로부터 수신)
    def calculate_position_size(self, 
                                signal_data: Dict[str, Any], 
                                current_price: float,
                                krw_balance: float) -> Optional[SignalOwlV1]:
        """
        Phase 3: 동적 리스크 및 포지션 규모 계산
        
        :param signal_data: SignalEngine이 생성한 신호 딕셔너리
                            (regime, tactic, sl_price, tp_price 등 포함)
        :param current_price: 현재가 (진입가 계산용)
        :param krw_balance: 현재 보유 KRW (주문 가능 금액)
        """
        
        try:
            # --- 1. 신호 데이터 추출 ---
            sl_price = signal_data.get('sl_price')
            tp_price = signal_data.get('tp_price')
            regime: Optional[MarketRegime] = signal_data.get('regime')
            
            if not all([sl_price, tp_price, regime]):
                raise ValueError("신호 딕셔너리에 'sl_price', 'tp_price' 또는 'regime'이 없습니다.")
            
            # (v3.5 레거시 점수 / Tactic 3 점수)
            score = signal_data.get('score', 12) # (점수 없으면 12점)

            # --- 2. [신규] (Phase 3) 동적 리스크 조절 ---
            
            # 2-1. (국면 기반)
            if regime == "BULL" or regime == "BEAR":
                # (강한 추세 확인 시 - TODO: HTF Confluence)
                regime_risk_multiplier = 1.0 # (임시 1.0배)
            elif regime == "RANGE":
                # (횡보 국면)
                regime_risk_multiplier = 0.8 # (0.8배)
            else:
                regime_risk_multiplier = 1.0

            # 2-2. (v3.5 레거시 점수 기반)
            if score >= 18:
                score_risk_multiplier = 1.5 
            elif score >= 16:
                score_risk_multiplier = 1.2
            elif score <= 13:
                score_risk_multiplier = 0.8
            else:
                score_risk_multiplier = 1.0 

            # (최종 리스크 배율: 두 배율 중 '더 보수적인(낮은)' 값을 선택)
            risk_multiplier = min(regime_risk_multiplier, score_risk_multiplier)
            
            # (최종 손실 확정 금액)
            loss_amount_krw = self.base_risk_amount * risk_multiplier
            
            # --- 3. 포지션 규모 계산 ---
            
            # 3-1. (LONG/SHORT 공통) 평균 진입가
            avg_entry_price = current_price
            
            # 3-2. (LONG/SHORT 공통) 1주당 손실액 (R)
            loss_per_coin = abs(avg_entry_price - sl_price)
            
            if loss_per_coin <= 0:
                raise ValueError(f"1주당 손실액이 0 이하입니다 (Avg Entry: {avg_entry_price}, SL: {sl_price}).")

            # 3-3. (LONG/SHORT 공통) 최종 진입 수량 (코인)
            final_volume_coin = loss_amount_krw / loss_per_coin
            
            # 3-4. (LONG/SHORT 공통) 총 투입 금액 (KRW)
            total_position_size_krw = final_volume_coin * avg_entry_price

            # --- 4. 잔고 확인 ---
            if total_position_size_krw > krw_balance:
                self.logger.warning(f"포지션 규모 축소: 계산된 금액({total_position_size_krw:,.0f}원)이 보유 KRW({krw_balance:,.0f}원)보다 많습니다.")
                
                total_position_size_krw = krw_balance * (1.0 - self.UPBIT_FEE_BUFFER)
                final_volume_coin = total_position_size_krw / avg_entry_price
                
                if total_position_size_krw < 5000:
                    self.logger.error(f"진입 취소: 보유 KRW가 최소 주문 금액(5,000원) 미만입니다.")
                    return None

            # --- 5. 최종 SignalOwlV1 객체 생성 ---
            final_signal = SignalOwlV1(
                symbol=signal_data.get('symbol'),
                signal_type=signal_data.get('signal_type', "LONG"),
                timestamp=datetime.now(),
                
                entry_price_avg=avg_entry_price,
                stop_loss_price=sl_price,
                target_price=tp_price,
                
                total_position_size_krw=total_position_size_krw,
                total_position_size_coin=final_volume_coin,
                
                signal_score=score,
                reason=signal_data.get('reason'),
                
                regime=regime,
                tactic=signal_data.get('tactic')
            )
            
            self.logger.info(f"[{final_signal.symbol}] 리스크 계산 완료 (국면: {regime}, 전술: {final_signal.tactic}, 리스크: {risk_multiplier:.1f}x)")
            self.logger.info(f"  > SL: {sl_price:,.2f}, Entry: {avg_entry_price:,.2f}, TP: {tp_price:,.2f}")
            self.logger.info(f"  > 1회 손실액: {loss_amount_krw:,.0f} KRW")
            self.logger.info(f"  > 총 투입 금액: {total_position_size_krw:,.0f} KRW ({final_volume_coin:.4f} 개)")
            
            return final_signal

        except Exception as e:
            self.logger.error(f"포지션 규모 계산 중 오류: {e}", exc_info=True)
            return None