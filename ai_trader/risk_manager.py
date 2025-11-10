# Athena_v1/ai_trader/risk_manager.py
"""
리스크 관리 (Strategy v3.5 3-3, 4단계)
신호 점수(Quality)에 따라 손실 확정 금액을 조절하고,
손절 라인을 기반으로 최종 포지션 규모(수량)를 계산합니다.
"""
from ai_trader.data_models import SignalV3_5 # Strategy 3.5 신호 객체 (가정)
from ai_trader.utils.logger import setup_logger

logger = setup_logger("RiskManager", "athena_v1.log")

class RiskManager:
    
    def __init__(self, total_capital: float, base_risk_per_trade_pct: float = 0.5):
        """
        :param total_capital: 총 투자 원금 (KRW)
        :param base_risk_per_trade_pct: 1회 거래당 기본 손실 허용률 (예: 0.5%)
        """
        self.total_capital = total_capital
        self.base_risk_pct = base_risk_per_trade_pct / 100.0 # (0.005)
        
        # 1회 거래당 기본 손실 확정 금액 (예: 1000만원 * 0.5% = 50,000원)
        self.base_risk_krw = self.total_capital * self.base_risk_pct
        
        logger.info(f"리스크 관리자 초기화. 총 자본: {total_capital:,.0f} KRW")
        logger.info(f"  기본 리스크 (1회): {self.base_risk_krw:,.0f} KRW ({base_risk_per_trade_pct}%)")

    def calculate_position_v3_5(self, signal: dict, current_price: float) -> SignalV3_5:
        """
        Strategy v3.5 (3-3, 4단계)를 기반으로 포지션 규모를 계산합니다.
        
        :param signal: SignalEngine에서 전달받은 신호 (dict)
                       (예: {'symbol': 'KRW-BTC', 'score': 16, 'ob_low': 90000, 'ob_height': 1000, ...})
        :param current_price: 현재가 (평균 진입가 계산 시 참고)
        :return: 최종 주문 정보가 담긴 SignalV3_5 객체
        """
        
        # --- (3-3) 리스크 조절 (신호 점수 기반) ---
        score = signal.get('score', 0)
        
        if score >= 18: # 초고득점
            risk_modifier = 1.5
        elif score >= 16: # 고득점
            risk_modifier = 1.2
        elif 14 <= score <= 15: # (전략 문서에 없는 '중간' 점수 추가)
             risk_modifier = 1.0
        elif 12 <= score <= 13: # 낮은 점수
             risk_modifier = 0.8
        else: # (12점 미만은 진입 안 함 - SignalEngine에서 필터링)
            logger.warning(f"[{signal['symbol']}] 리스크 계산 불가. (낮은 점수: {score})")
            return None

        # 최종 손실 확정 금액 (Risk Amount)
        risk_amount_krw = self.base_risk_krw * risk_modifier
        
        # --- (4단계) 포지션 규모 계산 ---
        
        # 1. 손절(SL) 라인 정의
        ob_low = signal.get('ob_low')
        ob_height = signal.get('ob_height')
        if not ob_low or not ob_height:
            logger.error(f"[{signal['symbol']}] SL 계산 불가 (OB 정보 누락)")
            return None
            
        # SL = OB 하단 - (OB 높이 * 0.2)
        stop_loss_price = ob_low - (ob_height * 0.2)
        
        # 2. 평균 진입가(Avg Entry) 계산
        # (전략: OB 상단(P0) ~ 70%(P70) 4분할 매수)
        # (단순화: 현재가가 이미 P70 근처라고 가정하고, Avg Entry를 현재가로 임시 사용)
        # TODO: 실제 분할매수 평단가 로직 구현
        avg_entry_price = current_price 
        
        # 3. 1주당 손실액 (Loss per Share)
        loss_per_coin = avg_entry_price - stop_loss_price
        
        if loss_per_coin <= 0:
            logger.warning(f"[{signal['symbol']}] 1주당 손실액 계산 오류. (AvgEntry: {avg_entry_price} <= SL: {stop_loss_price})")
            return None
            
        # 4. 최종 진입 수량 (코인)
        # 수량 = (손실 확정 금액) / (1주당 손실액)
        final_quantity_coin = risk_amount_krw / loss_per_coin
        
        # 5. 총 투입 금액 (KRW)
        total_investment_krw = final_quantity_coin * avg_entry_price

        # 업비트 최소 주문 금액 (5000 KRW) 확인
        if total_investment_krw < 5000:
            logger.warning(f"[{signal['symbol']}] 계산된 총 투입 금액이 최소 주문 금액(5000 KRW) 미만입니다. ({total_investment_krw:,.0f} KRW)")
            # (설정) 최소 금액으로 강제 진입
            total_investment_krw = 5000
            final_quantity_coin = 5000 / avg_entry_price
            
        # 1차 익절가 (TP) 계산 (예: 손익비 1:1.5)
        target_price = avg_entry_price + (loss_per_coin * 1.5)

        # 최종 주문 정보 객체 생성
        return SignalV3_5(
            symbol=signal['symbol'],
            signal_type='LONG',
            timestamp=datetime.now(),
            entry_price_avg=avg_entry_price,
            stop_loss_price=stop_loss_price,
            target_price=target_price,
            total_position_size_krw=total_investment_krw,
            total_position_size_coin=final_quantity_coin,
            signal_score=score,
            reason=signal.get('reason', 'N/A')
        )