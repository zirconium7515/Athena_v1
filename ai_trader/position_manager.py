# Athena_v1/ai_trader/position_manager.py
# [수정] 2024.11.11 - (오류) SyntaxError: invalid syntax (// 주석 수정)
# [수정] 2024.11.11 - (오류) NameError: 'Optional' is not defined (typing 임포트 추가)
# [수정] 2024.11.11 - (리팩토링) WebSocket 메시지 포맷 표준화 (type, payload)
# [수정] 2024.11.11 - (오류) 'NoneType' object has no attribute 'get' 버그 수정
# [수정] 2024.11.11 - (오류) 'str' object has no attribute 'get' 버그 수정 (Upbit 오류 포맷 2가지 처리)
# [수정] 2024.11.11 - (오류) InsufficientFundsBid (None)일 때 Exception 대신 Warning 처리 (봇 중지 방지)
# [수정] 2024.11.12 - (오류) AttributeError: 'SignalV3_5' object has no attribute 'strategy_id' 버그 수정
# [수정] 2024.11.14 - (Owl v1) ImportError: cannot import name 'SignalV3_5' (SignalOwlV1로 변경)
# [수정] 2024.11.15 - (Owl v1.1) S4: 국면 전환 시 청산 (Regime Change Exit) 로직 구현

import asyncio
import pandas as pd
from datetime import datetime
from typing import Callable, Awaitable, Dict, Any, Optional
from ai_trader.exchange_api import UpbitExchange
from ai_trader.mock_exchange import MockExchange
from ai_trader.database import Database
from ai_trader.risk_manager import RiskManager
from ai_trader.data_models import SignalOwlV1, Position, TradeLog
from ai_trader.utils.logger import setup_logger

# [신규] (Owl v1.1) S4 청산을 위한 국면 분석기 임포트
from ai_trader.strategy.regime import analyze_regime

class PositionManager:
    
    def __init__(self, 
                 exchange_api: UpbitExchange | MockExchange, 
                 db: Database, 
                 risk_manager: RiskManager, 
                 symbol: str,
                 broadcast_func: Callable[[Dict[str, Any]], Awaitable[None]]):
        
        self.exchange_api = exchange_api
        self.db = db
        self.risk_manager = risk_manager
        self.symbol = symbol
        self.broadcast = broadcast_func 
        self.logger = setup_logger(f"PositionMgr[{symbol}]", "athena_v1.log")
        
        self.current_position: Optional[Position] = None

    def get_position(self, symbol: str) -> Optional[Position]:
        if self.has_position() and self.symbol == symbol:
            return self.current_position
        return None

    def has_position(self) -> bool:
        return self.current_position is not None

    async def enter_position(self, signal: SignalOwlV1):
        if self.has_position():
            self.logger.warning(f"진입 시도 실패: 이미 {self.current_position.position_type} 포지션 보유 중 (진입가: {self.current_position.entry_price})")
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
            
        # (v1.1: 숏(Short) 매매 비활성화)
        if signal.signal_type == "LONG":
            order_side = "buy"
            log_msg_prefix = "시장가 매수"
        else:
            self.logger.error(f"[{self.symbol}] 숏(SHORT) 주문은 (Upbit 현물)에서 지원되지 않습니다.")
            return

        info_msg = f"[{self.symbol}] {log_msg_prefix} 주문 시도 (총 {total_krw_to_buy:,.0f} KRW)"
        self.logger.info(info_msg.replace(f"[{self.symbol}] ", ""))
        await self.broadcast({
            "type": "log",
            "payload": {"level": "info", "message": info_msg}
        })

        try:
            # --- 주문 실행 ---
            order_result = self.exchange_api.place_order(
                symbol=self.symbol,
                side=order_side,
                price=total_krw_to_buy,
                order_type='market'
            )
            
            if order_result is None:
                error_msg = f"[{self.symbol}] 주문 API 오류: API가 응답하지 않았습니다 (None). (잔고 부족 또는 Rate Limit)"
                self.logger.warning(error_msg.replace(f"[{self.symbol}] ", ""))
                await self.broadcast({
                    "type": "log",
                    "payload": {"level": "warn", "message": error_msg}
                })
                return 
            
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
                position_type=signal.signal_type, 
                entry_price=entry_price,
                volume=volume,
                target_price=signal.target_price,
                stop_loss_price=signal.stop_loss_price,
                entry_regime=signal.regime, # (진입 시점 국면 저장)
                strategy_id=signal.tactic 
            )

            success_msg = f"[{self.symbol}] {signal.signal_type} 포지션 진입 완료 (매수 평단가: {entry_price:,.2f}, 수량: {volume:.4f})"
            self.logger.info(success_msg.replace(f"[{self.symbol}] ", ""))
            await self.broadcast({
                "type": "log",
                "payload": {"level": "success", "message": success_msg}
            })
            
            # --- 거래 내역 DB 기록 ---
            log_entry = TradeLog(
                symbol=self.symbol,
                side=order_side,
                position_type=signal.signal_type, 
                price=entry_price,
                volume=volume,
                strategy_id=signal.tactic, 
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

    # [수정] (Owl v1.1) (current_data: pd.Series -> df_h1: pd.DataFrame)
    async def check_exit_conditions(self, position: Position, df_h1: pd.DataFrame):
        if not self.has_position():
            return
            
        current_price = df_h1.iloc[-1]['close']
        is_long = position.position_type == "LONG"
        
        # (S4가 S1/S2보다 우선순위가 높아야 함)

        # --- [신규] S4: 국면 전환 시 청산 (Regime Change Exit) ---
        # (df_h1이 국면 분석으로 인해 변경될 수 있으므로, .copy() 사용)
        new_regime = analyze_regime(df_h1.copy()) 
        entry_regime = position.entry_regime
        
        if new_regime != entry_regime:
            close_reason = None
            
            # (Case 1: '상승' 보고 샀는데, '횡보' 또는 '하락'으로 전환)
            if entry_regime == "BULL" and (new_regime == "RANGE" or new_regime == "BEAR"):
                close_reason = f"Regime Change (S4): BULL -> {new_regime}"
            
            # (Case 2: '횡보' 보고 샀는데, '하락'으로 전환)
            elif entry_regime == "RANGE" and new_regime == "BEAR":
                close_reason = f"Regime Change (S4): RANGE -> {new_regime}"

            if close_reason:
                warn_msg = f"[{self.symbol}] {close_reason}. 수익 보존/손실 제한을 위해 청산합니다."
                self.logger.warning(warn_msg.replace(f"[{self.symbol}] ", ""))
                await self.broadcast({
                    "type": "log",
                    "payload": {"level": "warn", "message": warn_msg}
                })
                await self.close_position(current_price, close_reason)
                return
        # --- (S4 로직 끝) ---


        # --- S1: 손절매 (Stop-Loss) ---
        if (is_long and current_price <= position.stop_loss_price) or \
           (not is_long and current_price >= position.stop_loss_price):
            
            sl_msg = f"SL: {position.stop_loss_price:,.2f}"
            warn_msg = f"[{self.symbol}] 손절(SL) 라인 도달! (현재가: {current_price:,.2f} / {sl_msg})"
            self.logger.warning(warn_msg.replace(f"[{self.symbol}] ", ""))
            await self.broadcast({
                "type": "log",
                "payload": {"level": "warn", "message": warn_msg}
            })
            await self.close_position(current_price, "StopLoss (S1)")
            return

        # --- S2: 1차 익절 (Take-Profit) ---
        elif (is_long and current_price >= position.target_price) or \
             (not is_long and current_price <= position.target_price):
            
            tp_msg = f"TP: {position.target_price:,.2f}"
            success_msg = f"[{self.symbol}] 익절(TP) 라인 도달! (현재가: {current_price:,.2f} / {tp_msg})"
            self.logger.info(success_msg.replace(f"[{self.symbol}] ", ""))
            await self.broadcast({
                "type": "log",
                "payload": {"level": "success", "message": success_msg}
            })
            # (TODO: 'Owl v1.2'에서 S2(50% 익절, 본절) 로직 구현 필요)
            await self.close_position(current_price, "TakeProfit (S2)")
            return
            
        else:
            self.logger.debug(f"포지션 유지 (국면: {entry_regime}) (현재가: {current_price:,.2f}, SL: {position.stop_loss_price:,.2f}, TP: {position.target_price:,.2f})")


    async def close_position(self, close_price: float, reason: str = "ManualClose"):
        if not self.has_position():
            self.logger.warning("포지션 청산 실패 (보유 포지션 없음).")
            return

        pos = self.current_position
        volume_to_sell = pos.volume
        
        # (v1.1: 숏(Short) 매매 비활성화)
        if pos.position_type == "LONG":
            order_side = "sell"
            log_msg_prefix = "시장가 매도(청산)"
            profit = (close_price - pos.entry_price) * volume_to_sell
            volume_or_price_arg = volume_to_sell # (매도 시에는 '수량' 전달)
        else:
            self.logger.error(f"[{self.symbol}] 숏(SHORT) 포지션 청산을 시도했으나, 지원되지 않습니다.")
            self.current_position = None
            return

        
        info_msg = f"[{self.symbol}] {log_msg_prefix} 주문 시도 (사유: {reason}, 수량: {volume_to_sell:.4f})"
        self.logger.info(info_msg.replace(f"[{self.symbol}] ", ""))
        await self.broadcast({
            "type": "log",
            "payload": {"level": "info", "message": info_msg}
        })

        try:
            # (LONG: 매도)
            order_result = self.exchange_api.place_order(
                symbol=self.symbol,
                side=order_side,
                volume=volume_or_price_arg, # (LONG: 수량 전달)
                price=0, # (시장가일 때 매도 'price'는 0)
                order_type='market'
            )

            if order_result is None:
                error_msg = f"[{self.symbol}] (청산) 주문 API 오류: API가 응답하지 않았습니다 (None). (Rate Limit 가능성)"
                self.logger.warning(error_msg.replace(f"[{self.symbol}] ", ""))
                await self.broadcast({
                    "type": "log",
                    "payload": {"level": "warn", "message": error_msg}
                })
                return 
            
            if 'error' in order_result:
                error_data = order_result['error']
                error_msg = ""
                if isinstance(error_data, dict):
                    error_msg = error_data.get('message', '알 수 없는 오류 (dict)')
                else:
                    error_msg = str(error_data)
                raise Exception(f"주문 API 오류: {error_msg}")

            await asyncio.sleep(3) 

            profit_msg_level = "success" if profit > 0 else "warn"
            success_msg = f"[{self.symbol}] {pos.position_type} 포지션 청산 완료 (청산가: {close_price:,.2f}). 실현 손익: {profit:,.0f} KRW"
            self.logger.info(success_msg.replace(f"[{self.symbol}] ", ""))
            await self.broadcast({
                "type": "log",
                "payload": {"level": profit_msg_level, "message": success_msg}
            })

            # --- 거래 내역 DB 기록 ---
            log_entry = TradeLog(
                symbol=self.symbol,
                side=order_side,
                position_type=pos.position_type, 
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