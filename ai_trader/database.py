# Athena_v1/ai_trader/database.py
"""
SQLite 데이터베이스 관리 (SQLAlchemy Core 사용)
거래 내역 (TradeLog) 저장 및 조회
"""
import sqlalchemy
from sqlalchemy import create_engine, Table, Column, Integer, String, Float, DateTime, MetaData
from datetime import datetime
from config import get_settings
from ai_trader.utils.logger import setup_logger

logger = setup_logger("Database", "athena_v1.log")

class Database:
    
    def __init__(self, db_name=None):
        if db_name is None:
            settings = get_settings()
            db_name = settings.get("DB_NAME", "athena_v1_trade_history.db")
            
        self.db_url = f"sqlite:///{db_name}"
        self.engine = create_engine(self.db_url)
        self.metadata = MetaData()
        
        # TradeLog 테이블 정의
        self.trade_logs = Table('trade_logs', self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('timestamp', DateTime, default=datetime.now),
            Column('symbol', String(30)),
            Column('side', String(10)), # 'buy' or 'sell'
            Column('price', Float),
            Column('volume', Float),
            Column('profit', Float, default=0.0),
            Column('strategy_id', String(50), default='v3.5'),
            Column('signal_score', Integer, default=0)
        )
        
    def create_tables(self):
        """ DB 파일 및 테이블 생성 """
        try:
            self.metadata.create_all(self.engine)
            logger.info(f"데이터베이스 테이블 생성/확인 완료: {self.db_url}")
        except Exception as e:
            logger.error(f"데이터베이스 테이블 생성 실패: {e}")

    def log_trade(self, symbol: str, side: str, price: float, volume: float, profit: float = 0.0, score: int = 0):
        """ 거래 내역 저장 """
        query = self.trade_logs.insert().values(
            timestamp=datetime.now(),
            symbol=symbol,
            side=side,
            price=price,
            volume=volume,
            profit=profit,
            strategy_id="v3.5",
            signal_score=score
        )
        try:
            with self.engine.connect() as conn:
                conn.execute(query)
                conn.commit() # SQLAlchemy 2.0 style commit
            logger.info(f"거래 기록 저장: {symbol} {side} {volume} @ {price}")
        except Exception as e:
            logger.error(f"거래 기록 저장 실패: {e}")

    def get_trade_history(self, symbol: str = None, limit: int = 100):
        """ 거래 내역 조회 """
        query = self.trade_logs.select().order_by(self.trade_logs.c.timestamp.desc()).limit(limit)
        
        if symbol:
            query = query.where(self.trade_logs.c.symbol == symbol)
            
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query)
                return result.fetchall() # [ (id, timestamp, ...), ... ]
        except Exception as e:
            logger.error(f"거래 내역 조회 실패: {e}")
            return []