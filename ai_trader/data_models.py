# Athena_v1/ai_trader/data_models.py
"""
프로젝트에서 사용되는 데이터 모델 (dataclasses)
(이전 버전의 TradeLog, SignalData 등을 필요시 여기에 정의)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class TradeLog:
    """ 거래 내역 (DB 저장용) """
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    symbol: str = ""
    side: str = "" # 'buy' or 'sell'
    price: float = 0.0
    volume: float = 0.0
    profit: float = 0.0 # 실현 손익
    strategy_id: str = "v3.5" # 사용된 전략
    signal_score: int = 0 # v3.5 점수

@dataclass
class Position:
    """ 현재 보유 포지션 (메모리 관리용) """
    symbol: str
    entry_price: float
    volume: float
    target_price: float # 익절가 (TP)
    stop_loss_price: float # 손절가 (SL)
    entry_timestamp: datetime = field(default_factory=datetime.now)
    strategy_id: str = "v3.5"

@dataclass
class SignalV3_5:
    """ Strategy v3.5 매매 신호 """
    symbol: str
    signal_type: str # 'LONG'
    timestamp: datetime # 신호 발생 시간
    entry_price_avg: float # 계산된 평균 진입가
    stop_loss_price: float # 계산된 손절 라인
    target_price: float # (Optional) 계산된 1차 익절 라인
    total_position_size_krw: float # 총 투입 금액 (KRW)
    total_position_size_coin: float # 최종 진입 수량 (Coin)
    signal_score: int # 최종 점수 (3단계)
    reason: str # 진입 근거 요약