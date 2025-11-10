# Athena_v1/ai_trader/position_manager.py
"""
보유 포지션 관리 (진입, 청산, 상태 업데이트)
Strategy v3.5에 따라 분할 진입 및 손절/익절 로직을 수행합니다.
"""
from ai_trader.exchange_api import UpbitExchange
from ai_trader.database import Database
from ai_trader.risk_manager import RiskManager
from ai_trader.data_models import Position, SignalV3_5
from ai_trader.utils.logger import setup_logger
import asyncio

class PositionManager:
    
    def __init__(self, exchange_api: UpbitExchange, db: Database, risk_manager: RiskManager, symbol: str):
        self.exchange_api = exchange_api
        self.db = db
        self.risk_manager = risk_manager
        self.symbol = symbol # 이 PositionManager는 단일 심볼만 관리
        
        # 현재 보유 포지션 (메모리 관리)
        self.current_position: Position = None
        self.logger = setup_logger(f"PositionManager[{symbol}]", "athena_v1.log")
        
        # TODO: 프로그램 시작 시, API를 통해 현재 보유 수량을 확인하여 self.current_position 복원
        # self.load_position_from_exchange() 
        
    def has_position(self) -> bool:
        """ 현재 이 심볼의 포지션을 보유하고 있는지 확인 """
        return self.current_position is not None

    async def enter_position(self, signal: SignalV3_5):
        """
        Strategy v3.5 신호에 따라 롱 포지션 진입 (분할 매수)
        """
        if self.has_position():
            self.logger.warning(f"이미 포지션 보유 중. 신규 진입 건너뜀. (신호 점수: {signal.signal_score})")
            return

        self.logger.info(f"포지션 진입 시도. (신호 점수: {signal.signal_score})")
        self.logger.info(f"  SL: {signal.stop_loss_price}, Avg Entry: {signal.entry_price_avg}")
        self.logger.info(f"  총 규모 (KRW): {signal.total_position_size_krw:,.0f} KRW")
        self.logger.info(f"  총 규모 (Coin): {signal.total_position_size_coin}")

        # Strategy v3.5 4단계: 분할 진입 실행
        # (예시: 여기서는 계산된 총 수량을 '시장가 매수'로 한 번에 진입)
        # (참고: v3.5는 4분할 매수를 권장하나, 구현 복잡성으로 인해 우선 시장가로 대체)
        
        try:
            # 시장가 매수 (총 KRW 금액 기준)
            order_result = self.exchange_api.place_order(
                symbol=self.symbol,
                side='buy',
                volume=0, # 시장가 매수 시 사용 안 함
                price=signal.total_position_size_krw, # 시장가 매수 총액 (KRW)
                order_type='market'
            )
            
            await asyncio.sleep(5) # 주문 체결 대기 (필수)
            
            # TODO: 주문 결과 확인 (체결 수량, 체결 단가)
            # (실제로는 get_order_details(order_result['uuid']) 등으로 체결 내역을 가져와야 함)
            
            # (임시) 평단가와 수량을 API에서 다시 가져옴
            avg_price = self.exchange_api.get_avg_buy_price(self.symbol)
            volume = self.exchange_api.get_balance(self.symbol) # KRW-XXX이므로, XXX 수량

            if volume == 0 or avg_price == 0:
                 self.logger.error("주문 실패 또는 잔고 조회 실패. 포지션 진입 취소.")
                 return

            self.current_position = Position(
                symbol=self.symbol,
                entry_price=avg_price,
                volume=volume,
                stop_loss_price=signal.stop_loss_price,
                target_price=signal.target_price # 1차 익절가
            )
            
            self.logger.info(f"롱 포지션 진입 완료: {volume} {self.symbol.split('-')[-1]} @ {avg_price}")
            
            # DB에 매수 기록
            self.db.log_trade(
                symbol=self.symbol,
                side='buy',
                price=avg_price,
                volume=volume,
                score=signal.signal_score
            )

        except Exception as e:
            self.logger.error(f"포지션 진입 중 오류: {e}")

    async def update_positions(self, current_price: float):
        """
        현재 가격을 기준으로 보유 포지션의 손절/익절 라인 확인
        """
        if not self.has_position() or current_price == 0.0:
            return

        pos = self.current_position
        
        # 1. 손절 (SL) 확인 (Strategy v3.5 - 5단계)
        if current_price <= pos.stop_loss_price:
            self.logger.warning(f"손절(SL) 라인 도달! [SL: {pos.stop_loss_price} / 현재가: {current_price}]")
            await self.close_position(reason="StopLoss")
            return

        # 2. 익절 (TP) 확인 (Strategy v3.5 - 6단계)
        # (v3.5는 복잡한 분할 익절/트레일링 스탑을 사용함)
        
        # (단순화) 1차 TP 도달 시 전량 매도
        if pos.target_price and current_price >= pos.target_price:
            self.logger.info(f"1차 익절(TP) 라인 도달! [TP: {pos.target_price} / 현재가: {current_price}]")
            await self.close_position(reason="TakeProfit")
            return
            
        # TODO: v3.5 6단계 (RBR 구조, 트레일링 스탑) 구현

    async def close_position(self, reason: str = "Manual"):
        """
        현재 보유 포지션 전량 매도 (시장가)
        """
        if not self.has_position():
            return
        
        pos = self.current_position
        volume_to_sell = pos.volume
        
        self.logger.info(f"포지션 청산 시도 ({reason}): {volume_to_sell} {self.symbol.split('-')[-1]}")
        
        try:
            # 시장가 매도 (보유 수량 기준)
            order_result = self.exchange_api.place_order(
                symbol=self.symbol,
                side='sell',
                volume=volume_to_sell,
                order_type='market'
            )
            
            await asyncio.sleep(5) # 체결 대기
            
            # TODO: 체결 내역 확인
            
            # (임시)
            current_price = await self.exchange_api.get_current_price(self.symbol)
            
            # 손익 계산
            profit = (current_price - pos.entry_price) * pos.volume
            
            self.logger.info(f"포지션 청산 완료. (매도가: {current_price})")
            self.logger.info(f"  매수 평단: {pos.entry_price}")
            self.logger.info(f"  실현 손익: {profit:,.0f} KRW")

            # DB에 매도 기록
            self.db.log_trade(
                symbol=self.symbol,
                side='sell',
                price=current_price,
                volume=volume_to_sell,
                profit=profit,
                score=0 # 매도 시에는 점수 없음
            )
            
            # 포지션 상태 초기화
            self.current_position = None

        except Exception as e:
            self.logger.error(f"포지션 청산 중 오류: {e}")