# Athena_v1/ai_trader/position_manager.py
# [수정] 2024.11.11 - (오류) SyntaxError: invalid syntax (// 주석 수정)
# [수정] 2024.11.11 - (오류) NameError: 'Optional' is not defined (typing 임포트 추가)
# [수정] 2024.11.11 - (리팩토링) WebSocket 메시지 포맷 표준화 (type, payload)
# [수정] 2024.11.11 - (오류) 'NoneType' object has no attribute 'get' 버그 수정
# [수정] 2024.11.11 - (오류) 'str' object has no attribute 'get' 버그 수정 (Upbit 오류 포맷 2가지 처리)
# [수정] 2024.11.11 - (오류) InsufficientFundsBid (None)일 때 Exception 대신 Warning 처리 (봇 중지 방지)

import asyncio
import pandas as pd
from datetime import datetime
from typing import Callable, Awaitable, Dict, Any, Optional
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
                 symbol: str,
                 broadcast_func: Callable[[Dict[str, Any]], Awaitable[None]]):
        
        self.exchange_api = exchange_api
        self.db = db
        self.risk_manager = risk_manager
        self.symbol = symbol
        self.broadcast = broadcast_func # (WebSocket 브로드캐스트 함수)
        self.logger = setup_logger(f"PositionMgr[{symbol}]", "athena_v1.log")
        
        self.current_position: Optional[Position] = None

    def get_position(self, symbol: str) -> Optional[Position]:
        if self.has_position() and self.symbol == symbol:
            return self.current_position
        return None

    def has_position(self) -> bool:
        return self.current_position is not None

    async def enter_position(self, signal: SignalV3_5):
        if self.has_position():
            self.logger.warning(f"진입 시도 실패: 이미 포지션 보유 중 (진입가: {self.current_position.entry_price})")
            return

        total_krw_to_buy = signal.total_position_size_krw
        
        if total_krw_to_buy < 5000:
            error_msg = f"[{self.symbol}] 주문 실패: 최소 주문 금액 (5000 KRW) 미만 (계산: {total_krw_to_buy:,.0f}원)"
            self.logger.error(error_msg.replace(f"[{self.symbol}] ", ""))
            await self.broadcast({
                "type": "log",
                "payload": {"level": "error", "message": error_msg}
            })
            return

        info_msg = f"[{self.symbol}] 시장가 매수 주문 시도 (총 {total_krw_to_buy:,.0f} KRW)"
        self.logger.info(info_msg.replace(f"[{self.symbol}] ", ""))
        await self.broadcast({
            "type": "log",
            "payload": {"level": "info", "message": info_msg}
        })

        try:
            # --- 시장가 매수 주문 실행 ---
            order_result = self.exchange_api.place_order(
                symbol=self.symbol,
                side='buy',
                price=total_krw_to_buy,
                order_type='market'
            )
            
            # [오류 수정] (None일 때 Exception 대신 Warning/return 처리)
            if order_result is None:
                # (Rate Limit 또는 InsufficientFundsBid)
                error_msg = f"[{self.symbol}] 주문 API 오류: API가 응답하지 않았습니다 (None). (잔고 부족 또는 Rate Limit)"
                self.logger.warning(error_msg.replace(f"[{self.symbol}] ", ""))
                await self.broadcast({
                    "type": "log",
                    "payload": {"level": "warn", "message": error_msg}
                })
                return # (봇을 중지시키지 않고, 이번 턴만 종료)
            
            if 'error' in order_result:
                error_data = order_result['error']
                error_msg = ""
                if isinstance(error_data, dict):
                    error_msg = error_data.get('message', '알 수 없는 오류 (dict)')
                else:
                    error_msg = str(error_data)
                raise Exception(f"주문 API 오류: {error_msg}")

            await asyncio.sleep(5) 
            
            entry_price = await self.exchange_api.get_avg_buy_price(self.symbol)
            balance_data = await self.exchange_api.get_balance(self.symbol, verbose=True)
            volume = float(balance_data.get('balance', 0.0))

            if entry_price == 0.0 or volume == 0.0:
                raise Exception("주문은 성공했으나, 체결 내역(평단가/수량)을 가져오지 못했습니다.")

            # --- 포지션 생성 (메모리) ---
            self.current_position = Position(
                symbol=self.symbol,
                entry_price=entry_price,
                volume=volume,
                target_price=signal.target_price,
                stop_loss_price=signal.stop_loss_price,
                strategy_id=signal.strategy_id,
            )

            success_msg = f"[{self.symbol}] 포지션 진입 완료 (매수 평단가: {entry_price:,.2f}, 수량: {volume:.4f})"
            self.logger.info(success_msg.replace(f"[{self.symbol}] ", ""))
            await self.broadcast({
                "type": "log",
                "payload": {"level": "success", "message": success_msg}
            })
            
            # --- 거래 내역 DB 기록 ---
            log_entry = TradeLog(
                symbol=self.symbol,
                side='buy',
                price=entry_price,
                volume=volume,
                strategy_id=signal.strategy_id,
                signal_score=signal.signal_score
            )
            self.db.log_trade(log_entry)

        except Exception as e:
            error_msg = f"[{self.symbol}] 포지션 진입 오류: {e}"
            self.logger.error(f"포지션 진입 중 심각한 오류: {e}", exc_info=True)
            await self.broadcast({
                "type": "log",
                "payload": {"level": "error", "message": error_msg}
            })
            self.current_position = None


    async def check_exit_conditions(self, position: Position, current_data: pd.Series):
        if not self.has_position():
            return
            
        current_price = current_data['close']

        if current_price <= position.stop_loss_price:
            warn_msg = f"[{self.symbol}] 손절(SL) 라인 도달! (현재가: {current_price:,.2f} <= SL: {position.stop_loss_price:,.2f})"
            self.logger.warning(warn_msg.replace(f"[{self.symbol}] ", ""))
            await self.broadcast({
                "type": "log",
                "payload": {"level": "warn", "message": warn_msg}
            })
            await self.close_position(current_price, "StopLoss")
            return

        elif current_price >= position.target_price:
            success_msg = f"[{self.symbol}] 익절(TP) 라인 도달! (현재가: {current_price:,.2f} >= TP: {position.target_price:,.2f})"
            self.logger.info(success_msg.replace(f"[{self.symbol}] ", ""))
            await self.broadcast({
                "type": "log",
                "payload": {"level": "success", "message": success_msg}
            })
            await self.close_position(current_price, "TakeProfit")
            return
            
        else:
            self.logger.debug(f"포지션 유지 (현재가: {current_price:,.2f}, SL: {position.stop_loss_price:,.2f}, TP: {position.target_price:,.2f})")


    async def close_position(self, close_price: float, reason: str = "ManualClose"):
        if not self.has_position():
            self.logger.warning("포지션 청산 실패 (보유 포지션 없음).")
            return

        pos = self.current_position
        volume_to_sell = pos.volume
        
        info_msg = f"[{self.symbol}] 시장가 매도(청산) 주문 시도 (사유: {reason}, 수량: {volume_to_sell:.4f})"
        self.logger.info(info_msg.replace(f"[{self.symbol}] ", ""))
        await self.broadcast({
            "type": "log",
            "payload": {"level": "info", "message": info_msg}
        })

        try:
            # --- 시장가 매도 주문 실행 ---
            order_result = self.exchange_api.place_order(
                symbol=self.symbol,
                side='sell',
                volume=volume_to_sell,
                order_type='market'
            )

            # [오류 수정] (None일 때 Exception 대신 Warning/return 처리)
            if order_result is None:
                # (Rate Limit 또는 InsufficientFundsBid)
                error_msg = f"[{self.symbol}] (청산) 주문 API 오류: API가 응답하지 않았습니다 (None). (Rate Limit 가능성)"
                self.logger.warning(error_msg.replace(f"[{self.symbol}] ", ""))
                await self.broadcast({
                    "type": "log",
                    "payload": {"level": "warn", "message": error_msg}
                })
                return # (봇을 중지시키지 않고, 이번 턴만 종료)
            
            if 'error' in order_result:
                error_data = order_result['error']
                error_msg = ""
                if isinstance(error_data, dict):
                    error_msg = error_data.get('message', '알 수 없는 오류 (dict)')
                else:
                    error_msg = str(error_data)
                raise Exception(f"주문 API 오류: {error_msg}")

            await asyncio.sleep(3) 

            # --- 실현 손익 (Profit) 계산 ---
            profit = (close_price - pos.entry_price) * volume_to_sell
            profit_msg_level = "success" if profit > 0 else "warn"
            success_msg = f"[{self.symbol}] 포지션 청산 완료 (청산가: {close_price:,.2f}). 실현 손익: {profit:,.0f} KRW"
            self.logger.info(success_msg.replace(f"[{self.symbol}] ", ""))
            await self.broadcast({
                "type": "log",
                "payload": {"level": profit_msg_level, "message": success_msg}
            })

            # --- 거래 내역 DB 기록 ---
            log_entry = TradeLog(
                symbol=self.symbol,
                side='sell',
                price=close_price,
                volume=volume_to_sell,
                profit=profit,
                strategy_id=pos.strategy_id,
                signal_score=0
            )
            self.db.log_trade(log_entry)

        except Exception as e:
            error_msg = f"[{self.symbol}] 포지션 청산 오류: {e}"
            self.logger.error(f"포지션 청산 중 심각한 오류: {e}", exc_info=True)
            await self.broadcast({
                "type": "log",
                "payload": {"level": "error", "message": error_msg}
            })
            
        finally:
            self.current_position = None