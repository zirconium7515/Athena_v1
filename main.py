# Athena_v1/main.py
"""
Athena v1 메인 애플리케이션
FastAPI를 사용하여 백엔드 서버를 실행하고,
React 프론트엔드와 WebSocket을 통해 통신하며,
선택된 코인들에 대한 트레이딩 봇을 비동기적으로 실행합니다.
"""

import uvicorn
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import threading
import time

from ai_trader.exchange_api import UpbitExchange
from ai_trader.data_manager import DataManager
from ai_trader.signal_engine import SignalEngine
from ai_trader.position_manager import PositionManager
from ai_trader.risk_manager import RiskManager
from ai_trader.database import Database
from ai_trader.utils.logger import setup_logger
from config import get_settings

# --- 초기 설정 ---
settings = get_settings()
logger = setup_logger("Athena_v1", "athena_v1.log")
app = FastAPI()

# CORS 설정 (React 앱이 기본적으로 3000 포트에서 실행되므로)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 앱 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 전역 변수 및 시스템 구성 요소 ---
db = Database("athena_v1_trade_history.db")
exchange_api = UpbitExchange()
active_bots: Dict[str, asyncio.Task] = {}  # { 'KRW-BTC': Task, ... }
websocket_clients: List[WebSocket] = [] # 연결된 GUI 클라이언트

# --- 트레이딩 봇 로직 ---
async def trading_bot_task(symbol: str):
    """
    개별 코인(symbol)에 대한 자동매매 비동기 태스크
    Strategy v3.5 기반으로 동작합니다.
    """
    logger.info(f"[{symbol}] 트레이딩 봇 시작...")
    
    # 이 코인을 위한 구성 요소 초기화
    # (참고: API, DB는 공유하고, 나머지는 코인별로 생성)
    data_manager = DataManager(exchange_api)
    risk_manager = RiskManager(total_capital=1_000_000) # 예시: 총 자본금 (설정 필요)
    position_manager = PositionManager(exchange_api, db, risk_manager, symbol)
    signal_engine = SignalEngine(data_manager, db, symbol)

    try:
        while True:
            # 1. 데이터 가져오기 (1시간봉 기준)
            df_h1 = await data_manager.fetch_ohlcv(symbol, timeframe='minutes60', count=200)
            
            if df_h1 is None or df_h1.empty:
                logger.warning(f"[{symbol}] 데이터 수신 실패. 60초 후 재시도.")
                await asyncio.sleep(60)
                continue

            # 2. Strategy v3.5 신호 생성
            # (signal_engine.py에 Strategy v3.5 로직 구현 필요)
            signal = signal_engine.generate_signal_v3_5(df_h1)

            current_price = await data_manager.get_current_price(symbol)
            
            # 3. 포지션 관리 (신호에 따라 진입/청산)
            if signal:
                logger.info(f"[{symbol}] 신호 감지: {signal}")
                # TODO: signal 객체에 따라 리스크 계산 및 포지션 진입/관리 로직 구현
                # 예: if signal['type'] == 'LONG':
                #    if not position_manager.has_position():
                #       # Strategy v3.5 4단계: 리스크/규모 계산
                #       order_details = risk_manager.calculate_position_v3_5(signal, current_price)
                #       await position_manager.enter_position(order_details)
                
                # GUI에 신호 전송
                await broadcast_log(f"[{symbol}] 신호: {signal['type']} at {signal['price']}")

            # 4. 현재 포지션 상태 업데이트 (예: 손절/익절 확인)
            await position_manager.update_positions(current_price)

            # 5. 주기적 실행 (예: 10분마다 확인)
            # (실제로는 1시간봉 완성을 기다리거나, 더 짧은 주기로 체크해야 함)
            await asyncio.sleep(600) # 10분 대기

    except asyncio.CancelledError:
        logger.info(f"[{symbol}] 트레이딩 봇 중지됨.")
    except Exception as e:
        logger.error(f"[{symbol}] 트레이딩 봇 오류 발생: {e}")
        await broadcast_log(f"[{symbol}] 오류: {e}")
    finally:
        # 봇 종료 시 정리 작업 (예: 포지션 청산)
        logger.info(f"[{symbol}] 봇 종료. 정리 작업 수행...")
        # await position_manager.close_all_positions() # 필요시 구현


# --- FastAPI 엔드포인트 ---

@app.get("/api/health")
async def health_check():
    """ 서버 상태 체크 """
    return {"status": "ok", "message": "Athena v1 Backend is running."}

@app.get("/api/markets")
async def get_markets():
    """
    거래 가능한 모든 KRW 마켓 목록을 반환합니다.
    (GUI에서 코인 선택 목록을 채우는 데 사용)
    """
    try:
        markets = await exchange_api.get_all_market_symbols()
        krw_markets = [m['market'] for m in markets if m['market'].startswith('KRW-')]
        krw_markets.sort()
        return {"markets": krw_markets}
    except Exception as e:
        logger.error(f"마켓 목록 조회 실패: {e}")
        return {"error": str(e)}

@app.post("/api/start")
async def start_bots(selected_coins: List[str]):
    """
    GUI에서 선택한 코인들 (selected_coins)에 대한 트레이딩 봇을 시작합니다.
    """
    logger.info(f"봇 시작 요청 수신: {selected_coins}")
    started = []
    for symbol in selected_coins:
        if symbol not in active_bots:
            # 새 비동기 태스크 생성 및 실행
            task = asyncio.create_task(trading_bot_task(symbol))
            active_bots[symbol] = task
            started.append(symbol)
            await broadcast_log(f"[{symbol}] 트레이딩 봇 시작.")
    
    return {"status": "started", "bots": started}

@app.post("/api/stop")
async def stop_bots(selected_coins: List[str]):
    """
    선택한 코인들의 트레이딩 봇을 중지합니다.
    """
    logger.info(f"봇 중지 요청 수신: {selected_coins}")
    stopped = []
    for symbol in selected_coins:
        if symbol in active_bots:
            task = active_bots[symbol]
            task.cancel() # 태스크 취소
            del active_bots[symbol]
            stopped.append(symbol)
            await broadcast_log(f"[{symbol}] 트레이딩 봇 중지.")
            
    return {"status": "stopped", "bots": stopped}

@app.get("/api/status")
async def get_status():
    """ 현재 실행 중인 봇 목록 반환 """
    return {"active_bots": list(active_bots.keys())}


# --- WebSocket (실시간 로그 및 상태 전송) ---

async def broadcast_log(message: str):
    """ 모든 연결된 GUI 클라이언트에게 메시지 전송 """
    logger.info(f"Broadcasting: {message}") # 서버 로그에도 기록
    for client in websocket_clients:
        try:
            await client.send_text(message)
        except Exception as e:
            logger.warning(f"WebSocket 전송 오류: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.append(websocket)
    logger.info("GUI 클라이언트 연결됨.")
    await websocket.send_text("[Athena v1] 서버에 연결되었습니다.")
    
    try:
        while True:
            # 클라이언트로부터 메시지를 받을 수도 있음 (현재는 수신 로직 없음)
            await websocket.receive_text() 
    except WebSocketDisconnect:
        logger.info("GUI 클라이언트 연결 끊김.")
        websocket_clients.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)


# --- 서버 실행 ---
if __name__ == "__main__":
    # DB 테이블 초기화
    db.create_tables()
    logger.info("Athena v1 서버 시작... (http://localhost:8000)")
    
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    # (참고: uvicorn main:app --host 0.0.0.0 --port 8000 --reload)
    # 위와 같이 터미널에서 실행하는 것을 권장합니다.
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)