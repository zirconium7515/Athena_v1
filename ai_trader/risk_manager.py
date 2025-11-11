# Athena_v1/ai_trader/risk_manager.py
# [수정] 2024.11.11 - (오류) SyntaxError: invalid syntax (// 주석 수정)
# [수정] 2024.11.11 - (오류) InsufficientFundsBid (수수료) 문제 해결 (99.9% 버퍼)
"""
리스크 관리자 (Strategy v3.5 - 3, 4단계)
(신호 점수에 따른 리스크 조절, 손절 라인 기반 포지션 규모 계산)
"""
from ai_trader.utils.logger import setup_logger
from ai_trader.data_models import SignalV3_5
from typing import Dict, Any, Optional
import math
from datetime import datetime

class RiskManager:
    
    # [신규] (오류 수정) 업비트 시장가 매수 수수료 (0.05%), 넉넉하게 0.1% 버퍼
    UPBIT_FEE_BUFFER = 0.001 # (0.1%)
    
    def __init__(self, 
                 total_capital: float, 
                 base_risk_per_trade_pct: float = 0.5):
        
        self.logger = setup_logger("RiskManager", "athena_v1.log")
        
        # 총 자본금 (예: 1,000,000 KRW)
        self.total_capital = total_capital
        # 1회 거래당 기본 리스크 (예: 0.5%)
        self.base_risk_per_trade_pct = base_risk_per_trade_pct
        
        # 기본 손실 확정 금액 (예: 1,000,000 * 0.5% = 5,000 KRW)
        self.base_risk_amount = self.total_capital * (self.base_risk_per_trade_pct / 100.0)
        
        self.logger.info(f"RiskManager 초기화: 총 자본금 {total_capital:,.0f} KRW, 기본 리스크 {self.base_risk_amount:,.0f} KRW ({base_risk_per_trade_pct}%)")

    def calculate_position_size(self, 
                                signal_data: Dict[str, Any], 
                                current_price: float,
                                krw_balance: float) -> Optional[SignalV3_5]:
        """
        v3.5 전략 3-3, 4단계 실행 (포지션 규모 계산)
        SignalEngine이 반환한 signal_data (dict)를 받아,
        최종 포지션 규모가 계산된 SignalV3_5 (dataclass) 객체를 반환합니다.
        
        :param signal_data: SignalEngine이 생성한 신호 딕셔너리
                            (score, ob_low, ob_high, pattern_tp 등 포함)
        :param current_price: 현재가 (진입가 계산용)
        :param krw_balance: 현재 보유 KRW (주문 가능 금액)
        """
        
        try:
            score = signal_data.get('score', 0)
            ob_low = signal_data.get('ob_low')
            ob_height = signal_data.get('ob_height')
            
            if not all([ob_low, ob_height]):
                raise ValueError("신호 딕셔너리에 'ob_low' 또는 'ob_height'가 없습니다.")

            # --- 3-3. 리스크 조절 (손실 확정 금액 계산) ---
            if score >= 18:
                risk_multiplier = 1.5 # 초고득점 (1.5배)
            elif score >= 16:
                risk_multiplier = 1.2 # 고득점 (1.2배)
            elif score <= 13:
                risk_multiplier = 0.8 # 낮은 점수 (0.8배)
            else:
                risk_multiplier = 1.0 # 기본 (14~15점)

            # (최종 손실 확정 금액)
            loss_amount_krw = self.base_risk_amount * risk_multiplier
            
            # --- 4단계: 포지션 규모 계산 ---
            
            # 1. 손절(SL) 라인 정의
            sl_price = ob_low - (ob_height * 0.2)
            
            # 2. 평균 진입가(Avg Entry) 계산
            avg_entry_price = current_price
            
            if avg_entry_price <= sl_price:
                self.logger.warning(f"진입 취소: 현재가({avg_entry_price})가 SL({sl_price})보다 낮음.")
                return None
                
            # 3. 1주당 손실액 (R)
            loss_per_coin = avg_entry_price - sl_price
            if loss_per_coin <= 0:
                raise ValueError("1주당 손실액이 0 이하입니다 (Avg Entry <= SL).")

            # 4. 최종 진입 수량 (코인)
            final_volume_coin = loss_amount_krw / loss_per_coin
            
            # 5. 총 투입 금액 (KRW)
            total_position_size_krw = final_volume_coin * avg_entry_price

            # --- 4-Extra: 잔고 확인 ---
            if total_position_size_krw > krw_balance:
                self.logger.warning(f"포지션 규모 축소: 계산된 금액({total_position_size_krw:,.0f}원)이 보유 KRW({krw_balance:,.0f}원)보다 많습니다.")
                
                # [오류 수정] (수수료 버퍼 0.1% 적용)
                total_position_size_krw = krw_balance * (1.0 - self.UPBIT_FEE_BUFFER)
                final_volume_coin = total_position_size_krw / avg_entry_price
                
                if total_position_size_krw < 5000:
                    self.logger.error(f"진입 취소: 보유 KRW가 최소 주문 금액(5,000원) 미만입니다.")
                    return None

            # --- 익절(TP) 라인 정의 ---
            tp_price = signal_data.get('pattern_tp')
            
            if tp_price is None or tp_price <= avg_entry_price:
                risk_reward_ratio = 2.0
                tp_price = avg_entry_price + (loss_per_coin * risk_reward_ratio)

            # --- 최종 SignalV3_5 객체 생성 ---
            final_signal = SignalV3_5(
                symbol=signal_data.get('symbol'),
                signal_type="LONG",
                timestamp=datetime.now(),
                
                entry_price_avg=avg_entry_price,
                stop_loss_price=sl_price,
                target_price=tp_price,
                
                total_position_size_krw=total_position_size_krw,
                total_position_size_coin=final_volume_coin,
                
                signal_score=score,
                reason=signal_data.get('reason', 'v3.5 Signal')
            )
            
            self.logger.info(f"[{final_signal.symbol}] 리스크 계산 완료 (점수: {score})")
            self.logger.info(f"  > SL: {sl_price:,.2f}, Entry: {avg_entry_price:,.2f}, TP: {tp_price:,.2f}")
            self.logger.info(f"  > 1회 손실액: {loss_amount_krw:,.0f} KRW")
            self.logger.info(f"  > 총 투입 금액: {total_position_size_krw:,.0f} KRW ({final_volume_coin:.4f} 개)")
            
            return final_signal

        except Exception as e:
            self.logger.error(f"v3.5 포지션 규모 계산 중 오류: {e}", exc_info=True)
            return None