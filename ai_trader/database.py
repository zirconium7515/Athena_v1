# Athena_v1/ai_trader/database.py
"""
데이터베이스 (SQLite) 관리
(거래 내역 저장 및 조회)
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import datetime

from ai_trader.utils.logger import setup_logger
from ai_trader.data_models import TradeLog

# [수정] 글로벌 스코프에서 로거 생성을 제거
# logger = setup_logger("Database", "athena_v1.log")

Base = declarative_base()

class TradeLogDB(Base):
    """ SQLAlchemy 모델 - trade_logs 테이블 """
    __tablename__ = 'trade_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    symbol = Column(String)
    side = Column(String) # 'buy' or 'sell'
    price = Column(Float)
    volume = Column(Float)
    profit = Column(Float)
    strategy_id = Column(String)
    signal_score = Column(Integer)

class Database:
    
    def __init__(self, db_name: str = "athena_v1_trade_history.db"):
        """
        데이터베이스 엔진 및 세션 초기화
        (FastAPI 비동기 환경 및 다중 스레드(봇) 접근을 위해
         check_same_thread=False 및 StaticPool 사용)
        """
        self.db_name = db_name
        self.engine = create_engine(
            f'sqlite:///{db_name}',
            echo=False,
            poolclass=StaticPool, # (경고) StaticPool은 단일 연결만 허용
            connect_args={'check_same_thread': False} 
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # [수정] 로거 생성을 __init__ 안으로 이동
        self.logger = setup_logger("Database", "athena_v1.log")

    def create_tables(self):
        """ 테이블 생성 (trade_logs) """
        try:
            Base.metadata.create_all(bind=self.engine)
            # [수정] logger -> self.logger
            self.logger.info(f"데이터베이스 '{self.db_name}' 및 테이블 'trade_logs' 초기화 완료.")
        except Exception as e:
            # [수정] logger -> self.logger
            self.logger.error(f"테이블 생성 실패: {e}")

    def log_trade(self, log_entry: TradeLog):
        """ 거래 내역(TradeLog 객체)을 DB에 저장 """
        session = self.SessionLocal()
        try:
            db_log = TradeLogDB(
                timestamp=log_entry.timestamp,
                symbol=log_entry.symbol,
                side=log_entry.side,
                price=log_entry.price,
                volume=log_entry.volume,
                profit=log_entry.profit,
                strategy_id=log_entry.strategy_id,
                signal_score=log_entry.signal_score
            )
            session.add(db_log)
            session.commit()
            # [수정] logger -> self.logger
            self.logger.info(f"거래 기록 저장: [{log_entry.symbol}] {log_entry.side} {log_entry.volume} @ {log_entry.price}")
        except Exception as e:
            session.rollback()
            # [수정] logger -> self.logger
            self.logger.error(f"거래 기록 저장 실패: {e}")
        finally:
            session.close()

    def get_trade_history(self, symbol: str = None, limit: int = 100) -> list[TradeLog]:
        """ DB에서 최근 거래 내역 조회 """
        session = self.SessionLocal()
        try:
            query = session.query(TradeLogDB)
            if symbol:
                query = query.filter(TradeLogDB.symbol == symbol)
            
            logs_db = query.order_by(TradeLogDB.timestamp.desc()).limit(limit).all()
            
            # (SQLAlchemy 객체 -> TradeLog (dataclass) 객체로 변환)
            logs_data = [
                TradeLog(
                    id=log.id,
                    timestamp=log.timestamp,
                    symbol=log.symbol,
                    side=log.side,
                    price=log.price,
                    volume=log.volume,
                    profit=log.profit,
                    strategy_id=log.strategy_id,
                    signal_score=log.signal_score
                ) for log in logs_db
            ]
            return logs_data
        except Exception as e:
            # [수정] logger -> self.logger
            self.logger.error(f"거래 내역 조회 실패: {e}")
            return []
        finally:
            session.close()