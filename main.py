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

# --- Python Import 경로 문제 해결 ---
# main.py가 실행되는 위치(현재 프로젝트 루트)를 Python 경로에 명시적으로 추가합니다.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# --- [수정] 모듈 임포트 순서 변경 (의존성 순서대로) ---

# 1. 기본 설정 및 유틸리티 (의존성 거의 없음)
from config import get_settings
from ai_trader.utils.logger import setup_logger

# 2. 핵심 API 및 DB (config, logger에 의존)
from ai_trader.database import Database
from ai_trader.exchange_api import UpbitExchange

# 3. 데이터 관리 (exchange_api에 의존)
from ai_trader.data_manager import DataManager

# 4. 전략 및 리스크 (data_manager, data_models에 의존)
from ai_trader.risk_manager import RiskManager
from ai_trader.signal_engine import SignalEngine

# 5. 포지션 관리 (상위 모듈들에 의존)
from ai_trader.position_manager import PositionManager
# --- [수정] 끝 ---


# --- 초기 설정 ---
settings = get_settings()
logger = setup_logger("Main", settings.get("LOG_FILE", "athena_v1.log"))
db = Database(settings.get("DB_NAME"))
db.create_tables()

# API 키 확인
if not settings.get("UPBIT_ACCESS_KEY") or not settings.get("UPBIT_SECRET_KEY"):
    logger.critical("API 키가 .env 파일에 설정되지 않았습니다! 프로그램을 종료합니다.")
    # (GUI가 없는 환경에서는 여기서 sys.exit(1)을 해야 할 수 있습니다)
    # sys.exit(1) 
else:
    logger.info(".env 파일에서 API 키 로드 완료.")


# --- FastAPI 앱 설정 ---
app = FastAPI()

# CORS 미들웨어 설정 (React 앱이 3000번 포트에서 8000번 API에 요청할 수 있도록 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 앱 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 봇 관리 ---
# { "KRW-BTC": <Task>, "KRW-ETH": <Task> }
active_bots: Dict[str, asyncio.Task] = {}
# 봇 중지를 위한 플래그 (더 안정적인 중지를 위해)
stop_flags: Dict[str, bool] = {}

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket 클라이언트 연결 (총 {len(self.active_connections)}명)")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket 클라이언트 연결 해제 (총 {len(self.active_connections)}명)")

    async def broadcast_log(self, message: str):
        """ 모든 연결된 클라이언트에게 로그 메시지 전송 """
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"WebSocket 전송 오류 (연결 해제됨): {e}")
                # (연결이 비정상적으로 끊긴 경우를 대비)
                # self.active_connections.remove(connection) # 동시성 문제 유발 가능

manager = ConnectionManager()

# --- 비동기 트레이딩 봇 태스크 ---
async def trading_bot_task(symbol: str):
    """
    개별 코인(심볼)에 대한 자동매매 로직을 실행하는 비동기 태스크
    """
    await manager.broadcast_log(f"[{symbol}] 트레이딩 봇 시작.")
    
    try:
        # 1. 모듈 초기화
        exchange = UpbitExchange()
        data_manager = DataManager(exchange)
        
        # TODO: 총 자본금 (KRW)을 API에서 가져오거나, 설정 파일에서 읽어와야 함
        # (임시) 총 자본 1,000,000 KRW, 1회 거래 리스크 0.5%
        total_capital = 1_000_000 
        risk_manager = RiskManager(total_capital=total_capital, base_risk_per_trade_pct=0.5)
        
        signal_engine = SignalEngine(data_manager, db, symbol)
        position_manager = PositionManager(exchange, db, risk_manager, symbol)
        
        # 2. 메인 루프 (봇이 중지 신호를 받을 때까지)
        while not stop_flags.get(symbol, False):
            try:
                # 2-1. 데이터 수집 (H1)
                df_h1 = await data_manager.fetch_ohlcv(symbol, timeframe='minutes60', count=200)
                
                if df_h1.empty:
                    logger.warning(f"[{symbol}] H1 데이터 수신 실패. 1분 후 재시도.")
                    await asyncio.sleep(60) # 데이터 없으면 1분 대기
                    continue

                current_price = df_h1['close'].iloc[-1]

                # 2-2. 포지션 상태 확인 (SL/TP)
                if position_manager.has_position():
                    await position_manager.update_positions(current_price)
                    
                    # (포지션이 있으면 10초마다 SL/TP 체크)
                    # (주의: v3.5는 H1 캔들 마감 기준이므로, 이 로직은 수정 필요)
                    # (임시) 1분마다 체크
                    await asyncio.sleep(60)
                    continue # 포지션이 있으면 신규 신호 탐색 안 함

                # 2-3. 신규 신호 탐색 (포지션이 없을 때만)
                signal = signal_engine.generate_signal_v3_5(df_h1)
                
                if signal:
                    # (신호 발생!)
                    logger.info(f"[{symbol}] 신호 감지 (점수: {signal.get('score')}). 리스크 계산 시작.")
                    await manager.broadcast_log(f"[{symbol}] 신호 감지 (점수: {signal.get('score')}). 리스크 계산 시작.")
                    
                    # 2-4. 리스크 계산 (v3.5 3-3, 4단계)
                    final_order_signal = risk_manager.calculate_position_v3_5(signal, current_price)
                    
                    if final_order_signal:
                        # 2-5. 포지션 진입
                        await manager.broadcast_log(f"[{symbol}] 포지션 진입 시도 (총 {final_order_signal.total_position_size_krw:,.0f} KRW).")
                        await position_manager.enter_position(final_order_signal)
                    else:
                        logger.warning(f"[{symbol}] 리스크 계산 실패. (진입 취소)")
                
                # 2-6. 다음 캔들까지 대기 (H1 갱신 주기)
                # (단순화) 10분마다 한 번씩 체크
                # (개선) H1 캔들이 갱신되는 시점(매시 정각 1분 후)까지 대기
                logger.debug(f"[{symbol}] 다음 신호 탐색까지 10분 대기...")
                await asyncio.sleep(600) # 10분
            
            except asyncio.CancelledError:
                # 봇 중지 (취소)
                raise # CancelledError를 바깥으로 다시 던져야 except절에서 처리됨
            
            except Exception as e:
                logger.error(f"[{symbol}] 봇 메인 루프 오류: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await manager.broadcast_log(f"[{symbol}] 오류 발생: {e}. 1분 후 재시도.")
                await asyncio.sleep(60) # 오류 발생 시 1분 대기
                
    except asyncio.CancelledError:
        logger.info(f"[{symbol}] 봇 중지 명령 수신 (Cancelled).")
        await manager.broadcast_log(f"[{symbol}] 트레이딩 봇 중지 완료.")
        
    except Exception as e:
        logger.critical(f"[{symbol}] 봇 초기화 또는 치명적 오류: {e}")
        import traceback
        logger.critical(traceback.format_exc())
        await manager.broadcast_log(f"[{symbol}] 봇 치명적 오류. 중지됨: {e}")
        
    finally:
        # 봇 종료 시, active_bots 딕셔너리에서 스스로 제거
        if symbol in active_bots:
            del active_bots[symbol]
        if symbol in stop_flags:
            del stop_flags[symbol]
        logger.info(f"[{symbol}] 봇 태스크 완전 종료.")


# --- FastAPI 엔드포인트 ---

@app.on_event("startup")
async def startup_event():
    # (GUI와는 별개로) 로그를 GUI로 전송하는 헬퍼 함수
    def log_broadcaster(message):
        # (참고) 이 함수는 동기 로거(logger.py)에서 호출되므로,
        # 비동기(manager.broadcast_log)를 직접 호출할 수 없습니다.
        # 따라서, 비동기 이벤트 루프에 작업을 예약합니다.
        try:
            # (이 부분은 uvicorn/FastAPI 환경에 따라 불안정할 수 있음)
            # (더 나은 방법: Queue 사용)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.call_soon_threadsafe(
                    asyncio.create_task, manager.broadcast_log(message)
                )
        except Exception as e:
            print(f"로그 브로드캐스팅 스케줄링 실패: {e}")

    # (임시) 콘솔 로거 핸들러에 브로드캐스터 추가
    # (더 나은 방법: custom handler를 logger.py에 구현)
    # logger.info("로그 브로드캐스터 설정 시도...")
    pass

@app.get("/api/markets")
async def get_markets():
    """ [GET] GUI에 업비트 KRW 마켓 목록을 반환합니다. """
    try:
        exchange = UpbitExchange()
        all_markets = await exchange.get_all_market_symbols()
        
        if all_markets:
            krw_markets = [
                m['market'] for m in all_markets 
                if m['market'].startswith('KRW-')
            ]
            krw_markets.sort() # 가나다순 정렬
            return {"markets": krw_markets}
        else:
            return {"error": "Upbit API에서 마켓 목록을 가져오지 못했습니다."}
            
    except Exception as e:
        logger.error(f"마켓 목록 조회 API 오류: {e}")
        return {"error": str(e)}

@app.get("/api/status")
async def get_status():
    """ [GET] 현재 실행 중인 봇 목록을 반환합니다. """
    return {"active_bots": list(active_bots.keys())}

@app.post("/api/start")
async def start_bots(symbols: List[str]):
    """ [POST] GUI에서 선택한 코인(심볼 목록)의 봇을 시작합니다. """
    started_bots = []
    for symbol in symbols:
        if symbol not in active_bots:
            logger.info(f"[{symbol}] 봇 시작 명령 수신.")
            stop_flags[symbol] = False # 중지 플래그 리셋
            # 비동기 태스크(trading_bot_task)를 생성하고 딕셔너리에 저장
            task = asyncio.create_task(trading_bot_task(symbol))
            active_bots[symbol] = task
            started_bots.append(symbol)
        else:
            logger.warning(f"[{symbol}] 봇 시작 명령 수신 (이미 실행 중).")
            
    return {"message": "봇 시작 완료", "bots": started_bots}

@app.post("/api/stop")
async def stop_bots(symbols: List[str]):
    """ [POST] GUI에서 선택한 코인(심볼 목록)의 봇을 중지합니다. """
    stopped_bots = []
    for symbol in symbols:
        if symbol in active_bots:
            logger.info(f"[{symbol}] 봇 중지 명령 수신.")
            stop_flags[symbol] = True # 루프 중지 플래그 설정
            
            task = active_bots.get(symbol)
            if task:
                task.cancel() # 태스크 취소 (CancelledError 발생)
                stopped_bots.append(symbol)
                # (실제 딕셔너리 제거는 봇이 스스로 종료될 때 (finally) 수행)
        else:
            logger.warning(f"[{symbol}] 봇 중지 명령 수신 (실행 중이지 않음).")
            
    return {"message": "봇 중지 완료", "bots": stopped_bots}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """ WebSocket 연결 엔드포인트 (실시간 로그 전송용) """
    await manager.connect(websocket)
    try:
        while True:
            # (클라이언트로부터 메시지를 받을 수도 있으나, 현재는 서버->클라 단방향)
            data = await websocket.receive_text()
            # (에코)
            # await manager.broadcast_log(f"Client says: {data}") 
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
        if websocket in manager.active_connections:
            manager.disconnect(websocket)


# --- 메인 실행 ---
if __name__ == "__main__":
    logger.info("========================================")
    logger.info("      Athena v1 백엔드 서버 시작       ")
    logger.info("========================================")
    
    # uvicorn.run()은 main.py를 직접 실행할 때 (python main.py) 사용
    # (uvicorn main:app --reload 방식에서는 이 코드가 실행되지 않음)
    
    # (참고) uvicorn.run()은 import 순서 문제와 무관하게
    #        'reload=True' 옵션을 사용할 경우 
    #        모듈을 두 번 임포트하려는 경향이 있어 오류를 유발할 수 있습니다.
    
    # 가장 안정적인 실행 방법:
    # (venv) C:\...> uvicorn main:app --host 127.0.0.1 --port 8000
    
    try:
        uvicorn.run(app, host="127.0.0.1", port=8000)
    except Exception as e:
        logger.critical(f"uvicorn 실행 실패: {e}")
        logger.critical("터미널에서 'uvicorn main:app --host 127.0.0.1 --port 8000'을(를) 직접 실행해 보세요.")