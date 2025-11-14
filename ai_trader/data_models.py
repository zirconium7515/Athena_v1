# Athena_v1/ai_trader/data_models.py
# [수정] 2024.11.11 - (오류) SyntaxError: invalid syntax (// 주석 수정)
# [수정] 2024.11.11 - (오류) 'float' object has no attribute 'get' (SignalV3_5 -> dict 수정)
# [수정] 2024.11.14 - (Owl v1) Signal, Position, TradeLog 모델 업그레이드

import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal # [신규]

# [신규] (Owl v1) 포지션 타입 (오타 방지)
PositionType = Literal["LONG", "SHORT"]
MarketRegime = Literal["BULL", "BEAR", "RANGE"]

# [수정] (SignalV3_5 -> SignalOwlV1)
@dataclass
class SignalOwlV1:
    """
    Owl v1 시그널 엔진이 생성하는 최종 진입 신호 객체
    (RiskManager가 이 객체를 받아 PositionManager에게 전달)
    """
    symbol: str
    signal_type: PositionType # [수정] (LONG/SHORT)
    timestamp: datetime
    
    # 리스크 관리
    entry_price_avg: float
    stop_loss_price: float
    target_price: float
    
    total_position_size_krw: float
    total_position_size_coin: float
    
    # (Owl v1 신규 필드)
    regime: MarketRegime # (진입 근거가 된 시장 국면)
    tactic: str # (진입 근거가 된 전술, 예: "Bullish OB", "Range Bounce")
    
    # (v3.5 계승 필드)
    signal_score: int
    reason: str = "v3.5 Signal" # (하위 호환성을 위해 유지)

# (Position: 봇이 현재 보유 중인 포지션)
@dataclass
class Position:
    """
    PositionManager가 현재 보유 중인 포지션을 관리하기 위한 객체
    (봇 메모리에 1개만 존재)
    """
    symbol: str
    position_type: PositionType # [신규] (LONG/SHORT)
    entry_price: float
    volume: float
    target_price: float
    stop_loss_price: float
    
    # (Owl v1 신규 필드)
    entry_regime: MarketRegime # (진입 시점의 시장 국면)
    
    # (v3.5 계승 필드)
    strategy_id: str = "v3.5" # (하위 호환성)
    timestamp: datetime = field(default_factory=datetime.now)

# (TradeLog: DB에 기록되는 모든 거래 내역)
@dataclass
class TradeLog:
    """
    모든 거래(진입/청산) 내역을 DB에 기록하기 위한 객체
    """
    symbol: str
    side: Literal["buy", "sell"]
    price: float
    volume: float
    
    position_type: PositionType # [신규] (LONG/SHORT)
    
    profit: float = 0.0
    strategy_id: str = "v3.5"
    signal_score: int = 0
    timestamp: datetime = field(default_factory=datetime.now)