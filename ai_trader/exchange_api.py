# Athena_v1/ai_trader/exchange_api.py
"""
Upbit 거래소 API 래퍼 (Wrapper)
(pyupbit 라이브러리 기반)
[수정] .env 대신 __init__에서 API 키를 전달받음
[수정] 2024.11.11 - get_market_all을 @classmethod에서 인스턴스 메소드로 변경
[수정] 2024.11.11 - get_market_all이 pyupbit 대신 aiohttp로 직접 API 호출
"""
import pyupbit
import asyncio
import aiohttp # [신규] aiohttp 임포트
from typing import Optional, List, Dict, Any

from ai_trader.utils.logger import setup_logger

class UpbitExchange:
    
    # [신규] aiohttp 세션 관리를 위한 클래스 변수
    _session: Optional[aiohttp.ClientSession] = None

    # [신규] aiohttp 클라이언트 세션 초기화 (비동기)
    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        """
        싱글톤 aiohttp 클라이언트 세션을 가져옵니다.
        """
        if cls._session is None or cls._session.closed:
            # 타임아웃 설정 (예: 5초)
            timeout = aiohttp.ClientTimeout(total=5)
            cls._session = aiohttp.ClientSession(timeout=timeout)
        return cls._session

    # [신규] aiohttp 세션 종료 (비동기)
    @classmethod
    async def close_session(cls):
        """
        싱글톤 aiohttp 세션을 닫습니다.
        """
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None
    
    def __init__(self, access_key: str = None, secret_key: str = None):
        """
        UpbitExchange 인스턴스를 초기화합니다.
        API 키가 제공되면 Private API용 pyupbit 클라이언트를 생성합니다.
        """
        self.logger = setup_logger("UpbitAPI", "athena_v1.log")
        
        self.access_key = access_key
        self.secret_key = secret_key
        
        try:
            self.upbit = pyupbit.Upbit(self.access_key, self.secret_key)
            if self.access_key:
                self.logger.info("Upbit (Private) API 클라이언트 초기화 완료.")
            else:
                self.logger.info("Upbit (Public) API 클라이언트 초기화 완료.")
        except Exception as e:
            self.logger.error(f"Upbit 클라이언트 초기화 실패: {e}")
            self.upbit = None

    # [수정] pyupbit 대신 aiohttp로 직접 API 호출
    async def get_market_all(self) -> List[Dict[str, Any]]:
        """
        [Public] 업비트 KRW 마켓 전체 목록 조회 (비동기 - aiohttp)
        (pyupbit.get_tickers 대신 업비트 공식 API 직접 호출)
        """
        url = "https://api.upbit.com/v1/market/all"
        params = {"isDetails": "true"} # 한글명, 유의종목 등 상세정보 포함
        
        try:
            session = await self.get_session()
            async with session.get(url, params=params) as response:
                response.raise_for_status() # (200 OK 아니면 오류 발생)
                all_markets = await response.json()
                
            if not all_markets:
                self.logger.warning("API로부터 마켓 목록을 받았으나 비어있습니다.")
                return []
                
            # KRW 마켓만 필터링하고 필요한 정보(market, korean_name)만 추출
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

    async def get_ohlcv(self, symbol: str, timeframe: str = 'minutes60', count: int = 200) -> List[Dict[str, Any]]:
        """
        [Public] OHLCV 데이터 조회 (비동기)
        (pyupbit의 정적 메소드 호출)
        """
        try:
            # (pyupbit.get_ohlcv는 동기 함수)
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None, 
                pyupbit.get_ohlcv, 
                symbol, 
                f"{timeframe.replace('minutes', 'minute')}", # (pyupbit 호환)
                count
            )
            
            if df is None:
                self.logger.warning(f"[{symbol}] OHLCV 데이터 없음 (None).")
                return []
                
            # (DataFrame을 JSON 리스트로 변환)
            df = df.reset_index()
            df.rename(columns={'index': 'candle_date_time_kst'}, inplace=True)
            return df.to_dict('records')
            
        except Exception as e:
            self.logger.error(f"[{symbol}] OHLCV 조회 실패: {e}")
            return []

    async def get_current_price(self, symbol: str) -> float:
        """ [Public] 현재가 조회 (비동기) """
        try:
            loop = asyncio.get_event_loop()
            price = await loop.run_in_executor(None, pyupbit.get_current_price, symbol)
            return float(price) if price else 0.0
        except Exception as e:
            self.logger.error(f"[{symbol}] 현재가 조회 실패: {e}")
            return 0.0

    # --- Private API (키 필요) ---

    async def get_balance(self, ticker: str = "KRW") -> Optional[float]:
        """ [Private] 특정 자산 잔고 조회 """
        if not self.upbit or not self.access_key:
            self.logger.warning("Private API 호출 실패 (API 키 없음).")
            return None
        try:
            loop = asyncio.get_event_loop()
            # (get_balance는 동기 함수)
            balance_data = await loop.run_in_executor(None, self.upbit.get_balance, ticker, verbose=True)
            
            # (verbose=True 사용 시, 반환값은 dict)
            if balance_data and 'balance' in balance_data:
                return float(balance_data['balance'])
            # (verbose=False 또는 ticker="KRW"가 아닌 코인 조회 시)
            elif isinstance(balance_data, (str, float)):
                 return float(balance_data)
                 
            self.logger.warning(f"[{ticker}] 잔고 조회 결과가 예상과 다름: {balance_data}")
            return 0.0
            
        except Exception as e:
            # (pyupbit이 오류를 raise할 수 있음. 예: 인증 실패)
            self.logger.error(f"[{ticker}] 잔고 조회 실패: {e}")
            # (오류 메시지를 API 호출자(main.py)에게 전달하기 위해 raise)
            raise e

    async def get_avg_buy_price(self, symbol: str) -> float:
        """ [Private] 특정 코인 매수 평단가 조회 """
        if not self.upbit or not self.access_key:
            return 0.0
        try:
            loop = asyncio.get_event_loop()
            # (get_balance는 동기 함수)
            balance_data = await loop.run_in_executor(None, self.upbit.get_balance, symbol, verbose=True)
            
            if balance_data and 'avg_buy_price' in balance_data:
                return float(balance_data['avg_buy_price'])
            return 0.0
        except Exception as e:
            self.logger.error(f"[{symbol}] 평단가 조회 실패: {e}")
            return 0.0
            
    def place_order(self, symbol: str, side: str, volume: float = 0, price: float = 0, order_type: str = 'limit') -> Optional[Dict[str, Any]]:
        """
        [Private] 주문 실행 (동기)
        (PositionManager에서 호출되며, 동기 실행 후 결과 즉시 반환)
        (주의: 이 함수는 비동기(async)가 아님! PositionManager에서 sleep 처리)
        
        :param volume: (지정가/시장가 매도) 수량
        :param price: (지정가) 가격 / (시장가 매수) 총액 (KRW)
        """
        if not self.upbit or not self.access_key:
            self.logger.error(f"[{symbol}] 주문 실패 (API 키 없음).")
            return None
            
        try:
            result = None
            if side == 'buy':
                if order_type == 'limit': # 지정가 매수
                    result = self.upbit.buy_limit_order(symbol, price, volume)
                elif order_type == 'market': # 시장가 매수
                    result = self.upbit.buy_market_order(symbol, price) # (price = 총액 KRW)
            
            elif side == 'sell':
                if order_type == 'limit': # 지정가 매도
                    result = self.upbit.sell_limit_order(symbol, price, volume)
                elif order_type == 'market': # 시장가 매도
                    result = self.upbit.sell_market_order(symbol, volume) # (volume = 수량)
            
            if result and 'error' in result:
                raise Exception(result['error'].get('message', 'Unknown error'))

            self.logger.info(f"주문 전송: {symbol} {side} {order_type} (결과: {result.get('uuid', 'Failed')})")
            return result
            
        except Exception as e:
            self.logger.error(f"[{symbol}] 주문 실행 실패: {e}")
            return None