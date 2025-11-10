# Athena_v1/ai_trader/position_manager.py
"""
포지션 관리자 (진입, 청산, SL/TP 모니터링)
(v3.5 전략 기반)
"""
import asyncio
from datetime import datetime
from ai_trader.exchange_api import UpbitExchange
from ai_trader.database import Database
from ai_trader.risk_manager import RiskManager
from ai_trader.data_models import SignalV3_5, Position, TradeLog
from ai_trader.utils.logger import setup_logger

class PositionManager:
    
    def __init__(self, 
                 exchange_api: UpbitExchange, 
                 db: Database, 
                 risk_manager: RiskManager, 
                 symbol: str):
        
        self.exchange_api = exchange_api
        self.db = db
        self.risk_manager = risk_manager
        self.symbol = symbol
        self.logger = setup_logger(f"PositionMgr[{symbol}]", "athena_v1.log")
        
        # --- 현재 포지션 상태 (메모리) ---
        # (봇이 재시작되면 초기화됨)
        # TODO: 봇 재시작 시 DB나 거래소 API에서 현재 포지션을 불러오는 로직 필요
        self.current_position: Position = None 

    def has_position(self) -> bool:
        """ 현재 해당 심볼의 포지션을 보유 중인지 확인 """
        return self.current_position is not None

    async def enter_position(self, signal: SignalV3_5):
        """
        v3.5 전략 4단계 (실행): 시장가 매수 주문 실행
        (v3.5는 분할 진입을 권장하나, 여기서는 단순화된 시장가 매수로 구현)
        """
        if self.has_position():
            self.logger.warning(f"진입 시도 실패: 이미 포지션 보유 중 (진입가: {self.current_position.entry_price})")
            return

        # (v3.5 4단계) RiskManager가 계산한 총 투입 금액(KRW)
        total_krw_to_buy = signal.total_position_size_krw
        
        # (업비트 최소 주문 금액 확인 - 예: 5000원)
        if total_krw_to_buy < 5000:
            self.logger.error(f"주문 실패: 최소 주문 금액 (5000 KRW) 미만 (계산된 금액: {total_krw_to_buy} KRW)")
            return

        self.logger.info(f"시장가 매수 주문 시도 (총 {total_krw_to_buy:,.0f} KRW)")

        try:
            # --- 시장가 매수 주문 실행 ---
            # (place_order는 동기 함수)
            order_result = self.exchange_api.place_order(
                symbol=self.symbol,
                side='buy',
                price=total_krw_to_buy, # 시장가 매수는 price에 총액(KRW)을 넣음
                order_type='market'
            )
            
            if order_result is None or 'uuid' not in order_result:
                raise Exception("주문 결과가 비어있거나 uuid가 없습니다.")

            # (주문 체결 대기 - 임시 5초)
            # TODO: 실제로는 get_order(uuid)로 체결 여부를 폴링(polling)해야 함
            await asyncio.sleep(5) 
            
            # --- 체결 정보 확인 (평단가) ---
            # (실제로는 get_order(uuid)의 'trades'에서 체결 내역을 가져와야 함)
            
            # (임시) get_avg_buy_price (보유 수량 평단가)를 진입 가격으로 사용
            entry_price = await self.exchange_api.get_avg_buy_price(self.symbol)
            # (임시) get_balance (보유 수량)
            volume = await self.exchange_api.get_balance(self.symbol)

            if entry_price == 0.0 or volume == 0.0:
                raise Exception("주문은 성공했으나, 체결 내역(평단가/수량)을 가져오지 못했습니다.")

            # --- 포지션 생성 (메모리) ---
            self.current_position = Position(
                symbol=self.symbol,
                entry_price=entry_price,
                volume=volume,
                target_price=signal.target_price,
                stop_loss_price=signal.stop_loss_price,
                strategy_id=signal.strategy_id
            )

            self.logger.info(f"포지션 진입 완료 (매수 평단가: {entry_price}, 수량: {volume})")
            
            # --- 거래 내역 DB 기록 ---
            log_entry = TradeLog(
                symbol=self.symbol,
                side='buy',
                price=entry_price,
                volume=volume,
                strategy_id=signal.strategy_id,
                signal_score=signal.score
            )
            self.db.log_trade(log_entry)

        except Exception as e:
            self.logger.error(f"포지션 진입 중 심각한 오류: {e}")
            self.current_position = None # (혹시 모르니 포지션 초기화)


    async def update_positions(self, current_price: float):
        """
        [매 루프 실행] 현재 가격을 기준으로 SL/TP 확인 및 포지션 종료
        """
        if not self.has_position():
            return

        pos = self.current_position

        # --- 1. 손절 (Stop Loss) 확인 ---
        if current_price <= pos.stop_loss_price:
            self.logger.warning(f"손절(SL) 라인 도달! (현재가: {current_price} <= SL: {pos.stop_loss_price})")
            await self.close_position(current_price, "StopLoss")

        # --- 2. 익절 (Take Profit) 확인 ---
        elif current_price >= pos.target_price:
            self.logger.info(f"익절(TP) 라인 도달! (현재가: {current_price} >= TP: {pos.target_price})")
            await self.close_position(current_price, "TakeProfit")
            
        # --- 3. (v3.5 4단계 - 미구현) 트레일링 스탑 (Trailing Stop) ---
        # TODO: v3.5의 '추격 SL' 로직 구현 필요
        # (예: if current_price > pos.entry_price * 1.05:
        #          pos.stop_loss_price = pos.entry_price * 1.02)
        
        else:
            # (포지션 유지)
            self.logger.debug(f"포지션 유지 (현재가: {current_price}, SL: {pos.stop_loss_price}, TP: {pos.target_price})")


    async def close_position(self, close_price: float, reason: str = "ManualClose"):
        """
        현재 보유 포지션을 시장가로 전량 매도 (청산)
        """
        if not self.has_position():
            self.logger.warning("포지션 청산 실패 (보유 포지션 없음).")
            return

        pos = self.current_position
        volume_to_sell = pos.volume
        
        self.logger.info(f"시장가 매도(청산) 주문 시도 (사유: {reason}, 수량: {volume_to_sell})")

        try:
            # --- 시장가 매도 주문 실행 ---
            order_result = self.exchange_api.place_order(
                symbol=self.symbol,
                side='sell',
                volume=volume_to_sell,
                order_type='market'
            )

            if order_result is None or 'uuid' not in order_result:
                raise Exception("매도 주문 결과가 비어있거나 uuid가 없습니다.")

            # (체결 대기 - 임시 3초)
            await asyncio.sleep(3) 

            # --- 실현 손익 (Profit) 계산 ---
            profit = (close_price - pos.entry_price) * volume_to_sell
            self.logger.info(f"포지션 청산 완료 (청산가: {close_price}). 실현 손익: {profit:,.0f} KRW")

            # --- 거래 내역 DB 기록 ---
            log_entry = TradeLog(
                symbol=self.symbol,
                side='sell',
                price=close_price,
                volume=volume_to_sell,
                profit=profit,
                strategy_id=pos.strategy_id,
                signal_score=0 # (청산 시에는 점수 없음)
            )
            self.db.log_trade(log_entry)

        except Exception as e:
            self.logger.error(f"포지션 청산 중 심각한 오류: {e}")
            # (오류가 나도 포지션은 초기화해야 함 - 수동 개입 필요)
            
        finally:
            # --- 포지션 초기화 (메모리) ---
            self.current_position = None