# Athena_v1/ai_trader/risk_manager.py
"""
리스크 관리 (Strategy v3.5 3-3, 4단계)
신호 점수(Quality)에 따라 손실 확정 금액을 조절하고,
손절 라인을 기반으로 최종 포지션 규모(수량)를 계산합니다.
"""
from ai_trader.data_models import SignalV3_5 # Strategy 3.5 신호 객체 (가정)
from ai_trader.utils.logger import setup_logger
# [수정] datetime 임포트 (SignalV3_5 생성 시 필요)
from datetime import datetime

# [수정] 글로벌 스코프에서 로거 생성을 제거
# logger = setup_logger("RiskManager", "athena_v1.log")

class RiskManager:
    
    def __init__(self, total_capital: float, base_risk_per_trade_pct: float = 0.5):
        """
        :param total_capital: 총 투자 원금 (KRW)
        :param base_risk_per_trade_pct: 1회 거래당 기본 손실 허용률 (예: 0.5%)
        """
        # [수정] 로거 생성을 __init__ 안으로 이동
        self.logger = setup_logger("RiskManager", "athena_v1.log")
        
        if total_capital <= 0:
            self.logger.critical("총 자본금이 0 이하입니다! 리스크 계산 불가.")
            self.total_capital = 0
            self.base_risk_pct = 0
            self.base_risk_krw = 0
        else:
            self.total_capital = total_capital
            self.base_risk_pct = base_risk_per_trade_pct / 100.0 # (0.005)
            # 1회 거래당 기본 손실 확정 금액 (예: 1000만원 * 0.5% = 50,000원)
            self.base_risk_krw = self.total_capital * self.base_risk_pct
        
        # [수정] logger -> self.logger
        self.logger.info(f"리스크 관리자 초기화. 총 자본: {self.total_capital:,.0f} KRW")
        self.logger.info(f"  기본 리스크 (1회): {self.base_risk_krw:,.0f} KRW ({base_risk_per_trade_pct}%)")

    def calculate_position_v3_5(self, signal: dict, current_price: float) -> SignalV3_5:
        """
        v3.5 전략 3-3, 4단계를 수행합니다.
        
        :param signal: SignalEngine에서 생성된 신호(dict)
        :param current_price: 현재 가격 (진입가 계산 참고용)
        :return: (SignalV3_5) 최종 주문 정보 객체 또는 None
        """
        
        if self.total_capital <= 0:
            self.logger.error(f"[{signal.get('symbol')}] 총 자본금 없음. 주문 생성 불가.")
            return None
            
        score = signal.get('score', 0)
        
        # 3-3. 리스크 조절 (손실 확정 금액)
        risk_modifier = 1.0
        if score >= 18:     # 초고득점
            risk_modifier = 1.5
        elif score >= 16:   # 고득점
            risk_modifier = 1.2
        elif 12 <= score <= 13: # 낮은 점수
             risk_modifier = 0.8
        else: # (12점 미만은 진입 안 함 - SignalEngine에서 필터링)
            # [수정] logger -> self.logger
            self.logger.warning(f"[{signal['symbol']}] 리스크 계산 불가. (낮은 점수: {score})")
            return None

        # 최종 손실 확정 금액 (Risk Amount)
        final_risk_krw = self.base_risk_krw * risk_modifier
        
        # 4. 포지션 규모 계산
        
        # 4-1. SL 라인 정의
        ob_low = signal.get('ob_low')
        ob_height = signal.get('ob_height')
        if not ob_low or not ob_height:
            # [수정] logger -> self.logger
            self.logger.error(f"[{signal['symbol']}] SL 계산 불가 (OB 정보 누락)")
            return None
            
        # SL = OB 하단 - (OB 높이 * 0.2)
        stop_loss_price = ob_low - (ob_height * 0.2)
        
        # 4-2. 평균 진입가(Avg Entry) 계산
        # (단순화) v3.5는 OB 상단~70% 4분할 매수지만, 
        #         여기서는 현재가(current_price)를 평균 진입가로 '가정'합니다.
        # (개선 필요)
        avg_entry_price = current_price
        
        if avg_entry_price <= stop_loss_price:
            self.logger.warning(f"[{signal['symbol']}] 현재가가 SL({stop_loss_price})보다 낮아 진입 불가. (현재가: {avg_entry_price})")
            return None

        # 4-3. 1주당 손실액
        loss_per_coin = avg_entry_price - stop_loss_price
        
        if loss_per_coin <= 0:
            # [수정] logger -> self.logger
            self.logger.warning(f"[{signal['symbol']}] 1주당 손실액 계산 오류. (AvgEntry: {avg_entry_price} <= SL: {stop_loss_price})")
            return None
            
        # 4-4. 최종 진입 수량 (코인)
        # (최종 진입 수량) = (손실 확정 금액) / (1주당 손실액)
        position_size_coin = final_risk_krw / loss_per_coin
        
        # 4-5. 총 투입 금액 (KRW)
        total_investment_krw = position_size_coin * avg_entry_price
        
        # 업비트 최소 주문 금액 (5000 KRW) 확인
        if total_investment_krw < 5000:
            # [수정] logger -> self.logger
            self.logger.warning(f"[{signal['symbol']}] 계산된 총 투입 금액이 최소 주문 금액(5000 KRW) 미만입니다. ({total_investment_krw:,.0f} KRW)")
            # (설정) 최소 금액으로 강제 진입
            total_investment_krw = 5000
            position_size_coin = total_investment_krw / avg_entry_price
            
        # TODO: v3.5 6단계 (TP 계산)
        # (임시) 1차 TP = (1주당 손실액 * 1.5) + avg_entry_price (R:R = 1:1.5)
        target_price = (loss_per_coin * 1.5) + avg_entry_price

        self.logger.info(f"[{signal['symbol']}] 리스크 계산 완료 (점수: {score})")
        self.logger.info(f"  손실 허용액: {final_risk_krw:,.0f} KRW")
        self.logger.info(f"  SL: {stop_loss_price:,.2f} / AvgEntry(가정): {avg_entry_price:,.2f}")
        self.logger.info(f"  총 투입액: {total_investment_krw:,.0f} KRW (수량: {position_size_coin})")

        # 최종 주문 객체 반환
        return SignalV3_5(
            symbol=signal['symbol'],
            signal_type='LONG',
            timestamp=datetime.now(),
            entry_price_avg=avg_entry_price,
            stop_loss_price=stop_loss_price,
            target_price=target_price,
            total_position_size_krw=total_investment_krw,
            total_position_size_coin=position_size_coin,
            signal_score=score,
            reason=signal.get('reason', 'N/A')
        )