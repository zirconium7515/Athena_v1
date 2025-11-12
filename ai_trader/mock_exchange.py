# Athena_v1/ai_trader/mock_exchange.py
# [신규] 2024.11.12 - (요청) 모의 투자 (페이퍼 트레이딩) 기능
# [수정] 2024.11.12 - (오류) 'Upbit' object has no attribute 'get_current_price' 버그 수정
"""
가상 거래소 (MockExchange)
UpbitExchange와 동일한 인터페이스(함수)를 가지지만,
실제 주문 대신 가상의 자산(10,000,000 KRW)을 이용해 모의 투자를 실행합니다.
"""
import pyupbit
import asyncio
import pandas as pd
from typing import Optional, List, Dict, Any
import uuid # [수정] (모의 주문 ID용)

# (중요) 공개(Public) API는 실제 UpbitExchange를 사용합니다.
from ai_trader.exchange_api import UpbitExchange
from ai_trader.utils.logger import setup_logger

class MockExchange:
    
    # (가상 자산)
    STARTING_CAPITAL_KRW = 10000000.0 # (시작 자본: 천만원)
    
    def __init__(self, access_key: str = None, secret_key: str = None):
        """
        모의 거래소 초기화
        (access_key, secret_key는 무시하지만, UpbitExchange와 인터페이스를 맞추기 위해 받음)
        """
        self.logger = setup_logger("MockExchange", "athena_v1.log")
        
        # 1. 공개(Public) API는 실제 업비트 데이터를 사용
        # (전략 테스트는 실제 데이터를 기반으로 해야 함)
        self.public_exchange = UpbitExchange(access_key=None, secret_key=None)
        
        # 2. 가상 자산 (Private)
        self.mock_krw_balance = self.STARTING_CAPITAL_KRW
        # (예: { "BTC": {"balance": 0.1, "avg_buy_price": 60000000}, ... })
        self.mock_assets: Dict[str, Dict[str, float]] = {}
        
        # [수정] (오류 수정) (self.pyupbit_public 객체 불필요 - 삭제)
        
        self.logger.info("--- 모의 투자 (MockExchange) 모드 활성화 ---")
        self.logger.info(f"가상 자본금 {self.mock_krw_balance:,.0f} KRW로 시작합니다.")

    # --- Public API (실제 데이터 Pass-through) ---

    async def get_market_all(self) -> List[Dict[str, Any]]:
        return await self.public_exchange.get_market_all()

    async def get_ohlcv(self, symbol: str, timeframe: str = 'minutes60', count: int = 200) -> Optional[pd.DataFrame]:
        return await self.public_exchange.get_ohlcv(symbol, timeframe, count)

    async def get_current_price(self, symbol: str | List[str]) -> Any:
        return await self.public_exchange.get_current_price(symbol)

    # --- Private API (가상 자산 반환) ---

    async def get_balance(self, ticker: str = "KRW", verbose: bool = False, use_cache: bool = True) -> Optional[float | List[Dict] | Dict]:
        """ (모의) 자산 조회 """
        
        # 1. 전체 자산 조회 (ticker=None, verbose=True)
        if ticker is None and verbose:
            summary = []
            
            # 1-1. KRW (원화)
            summary.append({
                "currency": "KRW",
                "balance": str(self.mock_krw_balance),
                "locked": "0.0",
                "avg_buy_price": "1.0"
            })
            
            # 1-2. 코인 자산
            for currency, data in self.mock_assets.items():
                summary.append({
                    "currency": currency,
                    "balance": str(data['balance']),
                    "locked": "0.0",
                    "avg_buy_price": str(data['avg_buy_price'])
                })
            
            return summary # (List[Dict] 반환)

        # 2. 특정 KRW 잔고 조회 (ticker="KRW", verbose=False)
        elif ticker == "KRW" and not verbose:
            return float(self.mock_krw_balance)
            
        # 3. 특정 코인 상세 조회 (ticker="BTC", verbose=True)
        elif ticker != "KRW" and verbose:
            coin_symbol = ticker.replace("KRW-", "")
            if coin_symbol in self.mock_assets:
                asset = self.mock_assets[coin_symbol]
                return {
                    "currency": coin_symbol,
                    "balance": str(asset['balance']),
                    "locked": "0.0",
                    "avg_buy_price": str(asset['avg_buy_price'])
                }
            else:
                return {
                    "currency": coin_symbol,
                    "balance": "0.0",
                    "locked": "0.0",
                    "avg_buy_price": "0.0"
                }
        
        self.logger.warning(f"알 수 없는 get_balance 호출: ticker={ticker}, verbose={verbose}")
        return 0.0 if not verbose else {"error": "Mock Error"}

    async def get_krw_balance(self, use_cache: bool = True) -> float:
        """ (모의) KRW 잔고 조회 """
        return float(self.mock_krw_balance)

    async def get_avg_buy_price(self, symbol: str) -> float:
        """ (모의) 평균 매수가 조회 """
        currency = symbol.replace("KRW-", "")
        if currency in self.mock_assets:
            return float(self.mock_assets[currency]['avg_buy_price'])
        return 0.0
        
    async def get_balance_no_cache(self, ticker: str = "KRW", verbose: bool = False) -> Optional[float | List[Dict] | Dict]:
        """ (모의) 비-캐시 자산 조회 (get_balance와 동일하게 작동) """
        return await self.get_balance(ticker, verbose, use_cache=False)

            
    def place_order(self, symbol: str, side: str, volume: float = 0, price: float = 0, order_type: str = 'limit') -> Optional[Dict[str, Any]]:
        """ (모의) 주문 실행 (동기) """
        
        try:
            # [오류 수정] (self.pyupbit_public.get_current_price -> pyupbit.get_current_price)
            current_price = pyupbit.get_current_price(symbol)
            if not current_price:
                raise Exception(f"현재가 조회 실패 (pyupbit.get_current_price가 None 반환)")
        except Exception as e:
            self.logger.error(f"[{symbol}] (모의) 주문 실패: 현재가 조회 실패. {e}")
            return {"error": "모의 주문 실패 (현재가 조회 실패)"}

        # --- 1. 시장가 매수 (price = 총액 KRW) ---
        if side == 'buy' and order_type == 'market':
            total_krw_to_buy = price
            
            fee = total_krw_to_buy * 0.0005
            
            if total_krw_to_buy + fee > self.mock_krw_balance:
                self.logger.warning(f"[{symbol}] (모의) 주문 실패: 잔고 부족 (요청: {total_krw_to_buy:,.0f} / 보유: {self.mock_krw_balance:,.0f})")
                return None # (InsufficientFundsBid 시뮬레이션)
            
            bought_volume = total_krw_to_buy / current_price
            currency = symbol.replace("KRW-", "")
            
            self.mock_krw_balance -= (total_krw_to_buy + fee)
            
            if currency not in self.mock_assets:
                self.mock_assets[currency] = {
                    "balance": bought_volume,
                    "avg_buy_price": current_price
                }
            else:
                existing_asset = self.mock_assets[currency]
                total_value = (existing_asset['avg_buy_price'] * existing_asset['balance']) + total_krw_to_buy
                total_volume = existing_asset['balance'] + bought_volume
                
                existing_asset['balance'] = total_volume
                existing_asset['avg_buy_price'] = total_value / total_volume
            
            self.logger.info(f"[{symbol}] (모의) 시장가 매수 성공: {bought_volume:.4f}개 @ {current_price:,.2f}")
            return {"uuid": f"mock-{uuid.uuid4()}", "side": "buy"} 

        # --- 2. 시장가 매도 (volume = 수량) ---
        elif side == 'sell' and order_type == 'market':
            volume_to_sell = volume
            currency = symbol.replace("KRW-", "")
            
            if currency not in self.mock_assets or volume_to_sell > self.mock_assets[currency]['balance']:
                self.logger.warning(f"[{symbol}] (모의) 주문 실패: 코인 수량 부족 (요청: {volume_to_sell} / 보유: {self.mock_assets.get(currency, {}).get('balance', 0)})")
                return None 

            sold_value_krw = volume_to_sell * current_price
            fee = sold_value_krw * 0.0005
            
            self.mock_krw_balance += (sold_value_krw - fee)
            
            self.mock_assets[currency]['balance'] -= volume_to_sell
            
            if self.mock_assets[currency]['balance'] < 1e-8: 
                del self.mock_assets[currency]

            self.logger.info(f"[{symbol}] (모의) 시장가 매도 성공: {volume_to_sell:.4f}개 @ {current_price:,.2f}")
            return {"uuid": f"mock-{uuid.uuid4()}", "side": "sell"} 

        else:
            self.logger.error(f"[{symbol}] (모의) 지원하지 않는 주문 유형: {side} {order_type}")
            return {"error": "모의 주문 실패 (지원하지 않는 유형)"}