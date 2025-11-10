# Athena_v1/ai_trader/exchange_api.py
"""
Upbit 거래소 API 래퍼 (pyupbit 및 aiohttp 기반 비동기 함수 활용)
"""
import pyupbit
import jwt
import uuid
import hashlib
import aiohttp
import asyncio
from urllib.parse import urlencode
from config import get_settings
from ai_trader.utils.logger import setup_logger

logger = setup_logger("ExchangeAPI", "athena_v1.log")

class UpbitExchange:
    
    def __init__(self):
        settings = get_settings()
        self.access_key = settings.get("UPBIT_ACCESS_KEY")
        self.secret_key = settings.get("UPBIT_SECRET_KEY")
        
        if not self.access_key or not self.secret_key:
            logger.warning("API 키가 .env 파일에 설정되지 않았습니다. 공개 API만 사용 가능합니다.")
            self.upbit = None
        else:
            try:
                self.upbit = pyupbit.Upbit(self.access_key, self.secret_key)
                balance = self.upbit.get_balance("KRW")
                logger.info(f"Upbit API 연결 성공. KRW 잔고: {balance}")
            except Exception as e:
                logger.error(f"Upbit API 연결 실패: {e}")
                self.upbit = None

    async def _request_async(self, method: str, url: str, params: dict = None, data: dict = None):
        """ 비동기 요청 헬퍼 (aiohttp) """
        headers = {"Accept": "application/json"}
        
        if self.access_key and self.secret_key:
            # API 인증 토큰 생성
            payload = {'access_key': self.access_key, 'nonce': str(uuid.uuid4())}
            if params:
                query_string = urlencode(params)
                payload['query_hash'] = hashlib.sha512(query_string.encode()).hexdigest()
                payload['query_hash_alg'] = 'SHA512'
            
            jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
            headers['Authorization'] = f'Bearer {jwt_token}'

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.request(method, url, params=params, json=data) as response:
                    response.raise_for_status() # 오류 발생 시 예외
                    return await response.json()
            except aiohttp.ClientResponseError as e:
                logger.error(f"API 요청 오류 ({e.status}): {e.message}")
                return None
            except Exception as e:
                logger.error(f"비동기 API 요청 중 알 수 없는 오류: {e}")
                return None

    async def get_all_market_symbols(self):
        """
        [비동기] 거래 가능한 모든 마켓 정보 (KRW, BTC, USDT)
        GUI에서 KRW 마켓을 필터링하기 위해 사용됩니다.
        """
        url = "https://api.upbit.com/v1/market/all"
        return await self._request_async("GET", url)

    async def get_ohlcv(self, symbol: str, timeframe: str = 'minutes60', count: int = 200):
        """
        [비동기] 캔들스틱 데이터 (OHLCV)
        timeframe: minutes1, minutes3, minutes5, minutes10, minutes15, minutes30, minutes60, minutes240, days, weeks, months
        """
        # pyupbit의 get_ohlcv는 내부적으로 requests(동기)를 사용하므로,
        # 비동기성을 유지하기 위해 Upbit API를 직접 호출합니다.
        
        # timeframe 변환 (Upbit API 형식에 맞게)
        if timeframe.startswith('minutes'):
            unit = timeframe
            url = f"https://api.upbit.com/v1/candles/{unit.replace('minutes', '')}"
        else: # days, weeks, months
            url = f"https://api.upbit.com/v1/candles/{timeframe}"
            
        params = {"market": symbol, "count": count}
        
        try:
            data = await self._request_async("GET", url, params=params)
            # 데이터가 비어있거나 오류가 난 경우
            if not data:
                logger.warning(f"[{symbol}] {timeframe} 캔들 데이터 수신 실패 (Empty Response)")
                return None
                
            # 데이터가 리스트 형태인지 확인
            if isinstance(data, list) and len(data) > 0:
                return data # pandas.DataFrame 변환은 DataManager에서 수행
            else:
                logger.warning(f"[{symbol}] {timeframe} 캔들 데이터 수신 실패: {data}")
                return None
                
        except Exception as e:
            logger.error(f"[{symbol}] {timeframe} 캔들 데이터 조회 중 오류: {e}")
            return None

    async def get_current_price(self, symbol: str):
        """ [비동기] 현재가 조회 """
        url = "https://api.upbit.com/v1/ticker"
        params = {"markets": symbol}
        data = await self._request_async("GET", url, params=params)
        if data and isinstance(data, list) and len(data) > 0:
            return data[0].get('trade_price')
        return None

    # --- (이하 pyupbit 동기 함수 - 필요시 비동기로 전환) ---

    def get_balance(self, currency: str):
        """ [동기] 특정 화폐 잔고 조회 """
        if not self.upbit: return 0
        try:
            return self.upbit.get_balance(currency)
        except Exception as e:
            logger.error(f"{currency} 잔고 조회 실패: {e}")
            return 0

    def get_avg_buy_price(self, currency: str):
        """ [동기] 특정 화폐 평단가 조회 """
        if not self.upbit: return 0
        try:
            balance = self.upbit.get_balance(currency, verbose=True)
            if balance and 'avg_buy_price' in balance:
                return float(balance['avg_buy_price'])
            return 0
        except Exception as e:
            logger.error(f"{currency} 평단가 조회 실패: {e}")
            return 0

    def place_order(self, symbol: str, side: str, volume: float, price: float = None, order_type: str = 'limit'):
        """ [동기] 주문 실행 (지정가/시장가) """
        if not self.upbit:
            logger.warning("API 키가 없어 주문을 실행할 수 없습니다. (시뮬레이션)")
            return {"uuid": f"simulated_{uuid.uuid4()}"} # 시뮬레이션 주문 ID

        try:
            if order_type == 'limit': # 지정가
                if price is None:
                    logger.error(f"[{symbol}] 지정가 주문에 가격이 필요합니다.")
                    return None
                if side == 'buy':
                    return self.upbit.buy_limit_order(symbol, price, volume)
                elif side == 'sell':
                    return self.upbit.sell_limit_order(symbol, price, volume)
            
            elif order_type == 'market': # 시장가
                if side == 'buy':
                    # 시장가 매수는 총 주문 금액(KRW) 기준
                    # volume을 총 주문 금액으로 해석 (주의: 이 API에서는 volume이 수량임)
                    # Strategy v3.5에서는 '총 투입 금액 (KRW)'이 계산되므로, 시장가 매수 사용
                    total_cost = price * volume # price를 총 KRW 금액으로 가정
                    return self.upbit.buy_market_order(symbol, total_cost) 
                elif side == 'sell':
                    # 시장가 매도는 수량(volume) 기준
                    return self.upbit.sell_market_order(symbol, volume)
            
            logger.error(f"[{symbol}] 지원하지 않는 주문 유형: {order_type} / {side}")
            return None

        except Exception as e:
            logger.error(f"[{symbol}] 주문 실패 ({side}, {order_type}): {e}")
            return None

    def cancel_order(self, order_uuid: str):
        """ [동기] 주문 취소 """
        if not self.upbit:
            logger.warning(f"API 키가 없어 주문을 취소할 수 없습니다. (UUID: {order_uuid})")
            return True
            
        try:
            result = self.upbit.cancel_order(order_uuid)
            logger.info(f"주문 취소 성공: {result}")
            return result
        except Exception as e:
            logger.error(f"주문 취소 실패 (UUID: {order_uuid}): {e}")
            return None