# Athena_v1/ai_trader/data_manager.py
# [수정] 2024.11.11 - (오류) SyntaxError: invalid syntax (// 주석 수정)
"""
데이터 수집 및 DataFrame 변환/관리
(exchange_api로부터 원본 데이터를 받아 pandas DataFrame으로 가공)
"""
import pandas as pd
from ai_trader.exchange_api import UpbitExchange
from ai_trader.utils.logger import setup_logger

class DataManager:
    
    def __init__(self, exchange_api: UpbitExchange):
        self.exchange_api = exchange_api
        # [수정] 로거 생성을 __init__ 안으로 이동
        self.logger = setup_logger("DataManager", "athena_v1.log")

    async def fetch_ohlcv(self, symbol: str, timeframe: str = 'minutes60', count: int = 200) -> pd.DataFrame:
        """
        지정된 심볼과 타임프레임의 OHLCV 데이터를 비동기적으로 가져와
        Pandas DataFrame으로 변환합니다.
        
        [수정] exchange_api.get_ohlcv()가 DataFrame을 반환하도록 변경됨
        """
        try:
            # exchange_api.get_ohlcv는 이제 KST 기준 DataFrame을 반환
            df = await self.exchange_api.get_ohlcv(symbol, timeframe, count)
            
            if df is None or df.empty:
                # [수정] logger -> self.logger
                self.logger.warning(f"[{symbol}] {timeframe} 데이터 없음.")
                return pd.DataFrame()

            # (pyupbit이 반환한 컬럼 이름: 'opening_price', 'trade_price' 등)
            # (표준 이름: 'open', 'close' 등으로 변경)
            df.rename(columns={
                'opening_price': 'open',
                'high_price': 'high',
                'low_price': 'low',
                'trade_price': 'close',
                'candle_acc_trade_volume': 'volume'
            }, inplace=True)
            
            # (날짜/시간(datetime) 인덱스는 pyupbit이 이미 설정함)
            
            # (필요한 컬럼만 선택)
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            # (데이터 타입 변환 - pyupbit이 이미 numeric으로 반환)
            
            # (API는 최신순으로 데이터를 주므로, 시간 오름차순으로 정렬)
            # (pyupbit은 기본적으로 오름차순으로 반환하므로 불필요)
            # df = df.sort_index(ascending=True) 
            
            # [수정] logger -> self.logger
            self.logger.debug(f"[{symbol}] {timeframe} 데이터 {len(df)}개 로드 완료 (KST).")
            return df

        except Exception as e:
            # [수정] logger -> self.logger
            self.logger.error(f"[{symbol}] {timeframe} DataFrame 변환 중 오류: {e}")
            return pd.DataFrame()

    async def get_current_price(self, symbol: str) -> float:
        """ 현재 가격 조회 """
        price = await self.exchange_api.get_current_price(symbol)
        return price if price else 0.0