# Athena_v1/ai_trader/data_manager.py
"""
데이터 수집 및 DataFrame 변환/관리
(exchange_api로부터 원본 데이터를 받아 pandas DataFrame으로 가공)
"""
import pandas as pd
from ai_trader.exchange_api import UpbitExchange
from ai_trader.utils.logger import setup_logger

# [수정] 글로벌 스코프에서 로거 생성을 제거
# logger = setup_logger("DataManager", "athena_v1.log")

class DataManager:
    
    def __init__(self, exchange_api: UpbitExchange):
        self.exchange_api = exchange_api
        # [수정] 로거 생성을 __init__ 안으로 이동
        self.logger = setup_logger("DataManager", "athena_v1.log")

    async def fetch_ohlcv(self, symbol: str, timeframe: str = 'minutes60', count: int = 200) -> pd.DataFrame:
        """
        지정된 심볼과 타임프레임의 OHLCV 데이터를 비동기적으로 가져와
        Pandas DataFrame으로 변환합니다.
        
        Strategy v3.5는 H1(minutes60)을 메인으로 사용합니다.
        """
        try:
            # exchange_api.get_ohlcv는 JSON 리스트를 반환
            raw_data = await self.exchange_api.get_ohlcv(symbol, timeframe, count)
            
            if raw_data is None or not isinstance(raw_data, list) or len(raw_data) == 0:
                # [수정] logger -> self.logger
                self.logger.warning(f"[{symbol}] {timeframe} 데이터 없음.")
                return pd.DataFrame()

            # DataFrame 생성
            df = pd.DataFrame(raw_data)
            
            # 필요한 컬럼만 선택 및 이름 변경
            df = df[['candle_date_time_kst', 'opening_price', 'high_price', 'low_price', 'trade_price', 'candle_acc_trade_volume']]
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            
            # 데이터 타입 변환
            df['datetime'] = pd.to_datetime(df['datetime'])
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            # 날짜/시간(datetime)을 인덱스로 설정
            df = df.set_index('datetime')
            
            # API는 최신순으로 데이터를 주므로, 시간 오름차순으로 정렬
            df = df.sort_index(ascending=True)
            
            # [수정] logger -> self.logger
            self.logger.debug(f"[{symbol}] {timeframe} 데이터 {len(df)}개 로드 완료.")
            return df

        except Exception as e:
            # [수정] logger -> self.logger
            self.logger.error(f"[{symbol}] {timeframe} DataFrame 변환 중 오류: {e}")
            return pd.DataFrame()

    async def get_current_price(self, symbol: str) -> float:
        """ 현재 가격 조회 """
        price = await self.exchange_api.get_current_price(symbol)
        return price if price else 0.0