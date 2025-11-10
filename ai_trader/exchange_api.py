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

# [수정] 글로벌 스코프에서 로거 생성을 제거
# logger = setup_logger("ExchangeAPI", "athena_v1.log")

class UpbitExchange:
    
    def __init__(self):
        # [수정] 로거 생성을 __init__ 안으로 이동
        self.logger = setup_logger("ExchangeAPI", "athena_v1.log")
        
        settings = get_settings()
        self.access_key = settings.get("UPBIT_ACCESS_KEY")
        self.secret_key = settings.get("UPBIT_SECRET_KEY")
        
        if not self.access_key or not self.secret_key:
            self.logger.warning("API 키가 .env 파일에 설정되지 않았습니다. 공개 API만 사용 가능합니다.")
            self.upbit = None
        else:
            try:
                self.upbit = pyupbit.Upbit(self.access_key, self.secret_key)
                balance = self.upbit.get_balance("KRW")
                self.logger.info(f"Upbit API 연결 성공. KRW 잔고: {balance}")
            except Exception as e:
                self.logger.error(f"Upbit API 연결 실패: {e}")
                self.upbit = None

    async def _request_async(self, method: str, url: str, params: dict = None, data: dict = None, is_private: bool = False):
        """ aiohttp를 사용한 비동기 API 요청 (공개/인증 모두) """
        
        headers = {"Accept": "application/json"}
        
        if is_private:
            if not self.access_key or not self.secret_key:
                self.logger.error("비공개 API 호출 시도 (키 없음).")
                return None
                
            payload = {
                'access_key': self.access_key,
                'nonce': str(uuid.uuid4()),
            }
            
            # 쿼리 파라미터나 POST 데이터가 있으면 JWT 페이로드에 추가
            query_string = None
            if params:
                query_string = urlencode(params)
                payload['query'] = query_string
                
            if data:
                # (참고) Upbit API는 POST/DELETE 시 data를 query처럼 취급하는 경우가 있음
                # (v1/orders API 사양 확인 필요)
                # 여기서는 params만 사용한다고 가정
                pass

            # JWT 토큰 생성
            jwt_token = jwt.encode(payload, self.secret_key)
            headers['Authorization'] = f'Bearer {jwt_token}'

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.request(method, url, params=params, json=data) as response:
                    response.raise_for_status() # 오류 발생 시 예외
                    return await response.json()
            except aiohttp.ClientResponseError as e:
                # [수정] logger -> self.logger
                self.logger.error(f"API 요청 오류 ({e.status}): {e.message}")
                return None
            except Exception as e:
                # [수정] logger -> self.logger
                self.logger.error(f"비동기 API 요청 중 알 수 없는 오류: {e}")
                return None

    async def get_all_market_symbols(self):
        """ (공개) 모든 마켓 코드 조회 (비동기) """
        url = "https://api.upbit.com/v1/market/all"
        return await self._request_async("GET", url)

    async def get_ohlcv(self, symbol: str, timeframe: str = 'minutes60', count: int = 200):
        """ (공개) 캔들 데이터 조회 (비동기) """
        # Upbit API 타임프레임 변환 (예: minutes60 -> minutes/60)
        tf_map = {
            'minutes1': 'minutes/1',
            'minutes3': 'minutes/3',
            'minutes5': 'minutes/5',
            'minutes10': 'minutes/10',
            'minutes15': 'minutes/15',
            'minutes30': 'minutes/30',
            'minutes60': 'minutes/60',
            'minutes240': 'minutes/240',
            'days': 'days',
            'weeks': 'weeks',
            'months': 'months'
        }
        
        api_timeframe = tf_map.get(timeframe)
        if not api_timeframe:
            self.logger.error(f"지원하지 않는 타임프레임: {timeframe}")
            return None

        url = f"https://api.upbit.com/v1/candles/{api_timeframe}"
        params = {
            "market": symbol,
            "count": count
        }
        
        try:
            data = await self._request_async("GET", url, params=params)
            # 데이터가 비어있거나 오류가 난 경우
            if not data:
                # [수정] logger -> self.logger
                self.logger.warning(f"[{symbol}] {timeframe} 캔들 데이터 수신 실패 (Empty Response)")
                return None
                
            # 데이터가 리스트 형태인지 확인
            if isinstance(data, list) and len(data) > 0:
                return data # pandas.DataFrame 변환은 DataManager에서 수행
            else:
                # [수정] logger -> self.logger
                self.logger.warning(f"[{symbol}] {timeframe} 캔들 데이터 수신 실패: {data}")
                return None
                
        except Exception as e:
            # [수정] logger -> self.logger
            self.logger.error(f"[{symbol}] {timeframe} 캔들 데이터 조회 중 오류: {e}")
            return None

    async def get_current_price(self, symbol: str):
        """ (공개) 현재가 조회 (비동기) - Ticker API 사용 """
        url = "https://api.upbit.com/v1/ticker"
        params = {"markets": symbol}
        data = await self._request_async("GET", url, params=params)
        if data and isinstance(data, list) and len(data) > 0:
            return data[0].get('trade_price')
        return None

    # --- (이하 pyupbit 동기 함수 - 필요시 비동기로 전환) ---

    def get_balance(self, currency: str):
        """ (인증) 특정 화폐 잔고 조회 (동기) """
        if not self.upbit: return 0
        try:
            return self.upbit.get_balance(currency)
        except Exception as e:
            # [수정] logger -> self.logger
            self.logger.error(f"{currency} 잔고 조회 실패: {e}")
            return 0

    def get_avg_buy_price(self, currency: str):
        """ (인증) 특정 화폐 평단가 조회 (동기) """
        if not self.upbit: return 0
        try:
            # currency가 'KRW-BTC'이면 'BTC'를 조회해야 함
            ticker = currency.split('-')[-1]
            balance = self.upbit.get_balance(ticker, verbose=True)
            
            if balance and 'avg_buy_price' in balance:
                return float(balance['avg_buy_price'])
            return 0
        except Exception as e:
            # [수정] logger -> self.logger
            self.logger.error(f"{currency} 평단가 조회 실패: {e}")
            return 0

    def place_order(self, symbol: str, side: str, volume: float, price: float = None, order_type: str = 'limit'):
        """ (인증) 주문 실행 (동기) """
        if not self.upbit:
            # [수정] logger -> self.logger
            self.logger.warning("API 키가 없어 주문을 실행할 수 없습니다. (시뮬레이션)")
            return {"uuid": f"simulated_{uuid.uuid4()}"} # 시뮬레이션 주문 ID

        try:
            if order_type == 'limit': # 지정가
                if price is None:
                    # [수정] logger -> self.logger
                    self.logger.error(f"[{symbol}] 지정가 주문에 가격이 필요합니다.")
                    return None
                if side == 'buy':
                    return self.upbit.buy_limit_order(symbol, price, volume)
                elif side == 'sell':
                    return self.upbit.sell_limit_order(symbol, price, volume)
                    
            elif order_type == 'market': # 시장가
                if side == 'buy':
                    # 시장가 매수는 총 주문 금액(KRW) 기준
                    # (PositionManager에서 price 파라미터에 총 주문액을 넣어줌)
                    total_cost = price 
                    return self.upbit.buy_market_order(symbol, total_cost) 
                elif side == 'sell':
                    # 시장가 매도는 수량(volume) 기준
                    return self.upbit.sell_market_order(symbol, volume)
            
            # [수정] logger -> self.logger
            self.logger.error(f"[{symbol}] 지원하지 않는 주문 유형: {order_type} / {side}")
            return None

        except Exception as e:
            # [수정] logger -> self.logger
            self.logger.error(f"[{symbol}] 주문 실패 ({side}, {order_type}): {e}")
            return None

    def cancel_order(self, order_uuid: str):
        """ (인증) 주문 취소 (동기) """
        if not self.upbit:
            # [수정] logger -> self.logger
            self.logger.warning(f"API 키가 없어 주문을 취소할 수 없습니다. (UUID: {order_uuid})")
            return True
            
        try:
            result = self.upbit.cancel_order(order_uuid)
            # [수정] logger -> self.logger
            self.logger.info(f"주문 취소 성공: {result}")
            return result
        except Exception as e:
            # [수정] logger -> self.logger
            self.logger.error(f"주문 취소 실패 (UUID: {order_uuid}): {e}")
            return None