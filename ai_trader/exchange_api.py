# Athena_v1/ai_trader/exchange_api.py
# [수정] 2024.11.11 - (오류) SyntaxError: invalid syntax (// 주석 수정)
# [수정] 2024.11.11 - (오류) get_market_all aiohttp로 직접 API 호출
# [수정] 2024.11.11 - (오류) NameError: 'pd' is not defined (pandas 임포트 추가)
# [수정] 2024.11.11 - (오류) InsufficientFundsBid (None) 반환 시, 'NoneType' object has no attribute 'get' 버그 수정
# [수정] 2024.11.11 - (오류) InsufficientFundsBid Race Condition 해결 (pyupbit 캐시 우회)

import pyupbit
import asyncio
import aiohttp 
import pandas as pd 
from typing import Optional, List, Dict, Any
import jwt  # [신규] (오류 수정) PyJWT 임포트
import uuid # [신규] (오류 수정) UUID 임포트

from ai_trader.utils.logger import setup_logger

class UpbitExchange:
    
    _session: Optional[aiohttp.ClientSession] = None

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            timeout = aiohttp.ClientTimeout(total=5)
            cls._session = aiohttp.ClientSession(timeout=timeout)
        return cls._session

    @classmethod
    async def close_session(cls):
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None
    
    def __init__(self, access_key: str = None, secret_key: str = None):
        self.logger = setup_logger("UpbitAPI", "athena_v1.log")
        
        self.access_key = access_key
        self.secret_key = secret_key
        
        try:
            if self.access_key and self.secret_key:
                self.upbit = pyupbit.Upbit(self.access_key, self.secret_key)
                self.logger.info("Upbit (Private) API 클라이언트 초기화 완료.")
            else:
                self.upbit = None 
                self.logger.info("Upbit (Public) API 클라이언트 초기화 완료.")
        except Exception as e:
            self.logger.error(f"Upbit 클라이언트 초기화 실패: {e}")
            self.upbit = None

    async def get_market_all(self) -> List[Dict[str, Any]]:
        url = "https://api.upbit.com/v1/market/all"
        params = {"isDetails": "true"} 
        
        try:
            session = await self.get_session()
            async with session.get(url, params=params) as response:
                response.raise_for_status() 
                all_markets = await response.json()
                
            if not all_markets:
                self.logger.warning("API로부터 마켓 목록을 받았으나 비어있습니다.")
                return []
                
            krw_markets = [
                {"market": m["market"], "korean_name": m["korean_name"]}
                for m in all_markets
                if m["market"].startswith("KRW-")
            ]
            
            self.logger.info(f"업비트 KRW 마켓 {len(krw_markets)}개 목록 로드 완료 (aiohttp).")
            return krw_markets
            
        except aiohttp.ClientError as e:
            self.logger.error(f"전체 마켓 조회 실패 (aiohttp): {e}")
            return []
        except Exception as e:
            self.logger.error(f"전체 마켓 조회 중 알 수 없는 오류: {e}")
            return []

    async def get_ohlcv(self, symbol: str, timeframe: str = 'minutes60', count: int = 200) -> Optional[pd.DataFrame]:
        try:
            loop = asyncio.get_running_loop()
            
            pyupbit_interval = timeframe.replace('minutes', 'minute')
            
            df = await loop.run_in_executor(
                None, 
                pyupbit.get_ohlcv, 
                symbol, 
                pyupbit_interval, 
                count
            )
            
            if df is None:
                self.logger.warning(f"[{symbol}] {timeframe} OHLCV 데이터 없음 (None).")
                return pd.DataFrame() 
                
            return df
            
        except Exception as e:
            self.logger.error(f"[{symbol}] {timeframe} OHLCV 조회 실패: {e}")
            return pd.DataFrame() 

    async def get_current_price(self, symbol: str) -> float:
        try:
            loop = asyncio.get_running_loop()
            price = await loop.run_in_executor(None, pyupbit.get_current_price, symbol)
            return float(price) if price else 0.0
        except Exception as e:
            self.logger.error(f"[{symbol}] 현재가 조회 실패: {e}")
            return 0.0

    # --- Private API (키 필요) ---

    # [수정] (오류 수정) (use_cache 파라미터 추가)
    async def get_balance(self, ticker: str = "KRW", verbose: bool = False, use_cache: bool = True) -> Optional[float]:
        if not self.upbit or not self.access_key:
            self.logger.warning(f"[{ticker}] 잔고 조회 실패 (Private API 키 없음).")
            if verbose:
                return {"error": "API key is not set."}
            return None
            
        try:
            # (캐시 사용 O: pyupbit 라이브러리 사용)
            if use_cache:
                loop = asyncio.get_running_loop()
                balance_data = await loop.run_in_executor(None, self.upbit.get_balance, ticker, verbose)
            
            # (캐시 사용 X: aiohttp 직접 호출)
            else:
                self.logger.debug(f"[{ticker}] (No-Cache) 잔고 조회 시도...")
                balance_data = await self.get_balance_no_cache(ticker, verbose)
            
            if verbose:
                return balance_data 
            else:
                return float(balance_data) 
            
        except Exception as e:
            self.logger.error(f"[{ticker}] 잔고 조회 실패: {e}")
            if verbose:
                return {"error": str(e)}
            return None 
            
    # [수정] (오류 수정) (use_cache 파라미터 전달)
    async def get_krw_balance(self, use_cache: bool = True) -> float:
        balance = await self.get_balance(ticker="KRW", verbose=False, use_cache=use_cache)
        return balance if balance else 0.0

    async def get_avg_buy_price(self, symbol: str) -> float:
        balance_data = await self.get_balance(ticker=symbol, verbose=True, use_cache=True)
        if balance_data and 'avg_buy_price' in balance_data:
            return float(balance_data['avg_buy_price'])
        return 0.0
        
    # [신규] (오류 수정) pyupbit 캐시 우회를 위한 비동기, 비캐시 잔고 조회
    async def get_balance_no_cache(self, ticker: str = "KRW", verbose: bool = False) -> Optional[float]:
        """
        pyupbit의 lru_cache를 우회하여 API로 직접 잔고를 조회합니다 (aiohttp).
        """
        if not self.access_key or not self.secret_key:
            return None

        try:
            # (JWT 토큰 생성)
            payload = {
                'access_key': self.access_key,
                'nonce': str(uuid.uuid4()),
            }
            jwt_token = jwt.encode(payload, self.secret_key)
            headers = {'Authorization': f'Bearer {jwt_token}'}

            # (API 요청)
            session = await self.get_session()
            url = "https://api.upbit.com/v1/accounts"
            
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                all_accounts = await response.json()

            # (결과 파싱)
            for account in all_accounts:
                if account['currency'] == ticker:
                    if verbose:
                        return account # (상세 정보 dict 반환)
                    else:
                        return float(account['balance']) # (잔고 float 반환)
            
            # (해당 티커를 찾지 못한 경우)
            if verbose:
                return {"currency": ticker, "balance": "0.0", "locked": "0.0", "avg_buy_price": "0.0"}
            else:
                return 0.0

        except aiohttp.ClientError as e:
            self.logger.error(f"[{ticker}] (No-Cache) 잔고 조회 실패 (aiohttp): {e}")
            if verbose:
                return {"error": str(e)}
            return None
        except Exception as e:
            self.logger.error(f"[{ticker}] (No-Cache) 잔고 조회 중 알 수 없는 오류: {e}")
            if verbose:
                return {"error": str(e)}
            return None

            
    def place_order(self, symbol: str, side: str, volume: float = 0, price: float = 0, order_type: str = 'limit') -> Optional[Dict[str, Any]]:
        """
        [Private] 주문 실행 (동기)
        (pyupbit의 동기 함수를 사용 - 봇 태스크 내부에서 실행됨)
        """
        if not self.upbit or not self.access_key:
            self.logger.error(f"[{symbol}] 주문 실패 (API 키 없음).")
            return {"error": "API key is not set."}
            
        try:
            result = None
            if side == 'buy':
                if order_type == 'limit': 
                    result = self.upbit.buy_limit_order(symbol, price, volume)
                elif order_type == 'market': 
                    result = self.upbit.buy_market_order(symbol, price) 
            
            elif side == 'sell':
                if order_type == 'limit': 
                    result = self.upbit.sell_limit_order(symbol, price, volume)
                elif order_type == 'market': 
                    result = self.upbit.sell_market_order(symbol, volume) 
            
            if result is None:
                self.logger.warning(f"[{symbol}] 주문 API가 None을 반환했습니다. (InsufficientFundsBid 또는 Rate Limit 가능성)")
                return None
            
            if 'error' in result:
                # (pyupbit이 반환하는 오류 dict)
                raise Exception(result['error'].get('message', 'Unknown error'))

            self.logger.info(f"주문 전송: {symbol} {side} {order_type} (결과: {result.get('uuid', 'Success')})")
            return result
            
        except Exception as e:
            self.logger.error(f"[{symbol}] 주문 실행 실패: {e}")
            return {"error": str(e)}