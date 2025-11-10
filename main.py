# Athena_v1/main.py
# [수정] GUI에서 API 키를 입력받도록 대폭 수정

import sys
import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import List, Dict, Any, Set
import logging

# --- 경로 설정 (기존 ImportError 해결) ---
# (이 코드는 `python main.py` 실행 시 필요)
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- 경로 설정 끝 ---

# --- 모듈 임포트 (순서 재조정됨) ---
from config import get_settings
from ai_trader.utils.logger import setup_logger
from ai_trader.exchange_api import UpbitExchange
from ai_trader.database import Database
from ai_trader.data_manager import DataManager
from ai_trader.signal_engine import SignalEngine
from ai_trader.risk_manager import RiskManager
from ai_trader.position_manager import PositionManager
from ai_trader.data_models import SignalV3_5
# --- 모듈 임포트 끝 ---


# --- 기본 설정 ---
# (주의: 이제 .env에서 API 키를 읽어오지 않음)
settings = get_settings()
db = Database(settings.get("DB_NAME"))
db.create_tables()

# 메인 로거 (서버 활동용)
logger = setup_logger("MainApp", settings.get("LOG_FILE"))

# FastAPI 앱 생성
app = FastAPI()

# --- CORS 설정 ---
# (React 개발 서버(localhost:3000)에서의 요청 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- [신규] API 키 저장을 위한 글로벌 변수 ---
api_keys = {
    "access": None,
    "secret": None
}

# --- 공용 API 호출을 위한 UpbitExchange 인스턴스 (키 없음) ---
public_exchange = UpbitExchange()

# --- 봇 관리 ---
# (실행 중인 봇 태스크 저장: {'KRW-BTC': asyncio.Task, ...})
active_bots: Dict[str, asyncio.Task] = {}

# --- WebSocket 관리 (GUI 로그 전송용) ---
connected_clients: Set[WebSocket] = set()

async def send_log_to_clients(message: str, level: str = "info"):
    """ 연결된 모든 GUI 클라이언트에게 로그 메시지 전송 """
    log_entry = {"message": message, "level": level}
    for ws in connected_clients:
        try:
            await ws.send_json(log_entry)
        except Exception:
            # (연결 끊김 등 예외 발생 시, 세트에서 제거는 on_disconnect에서 처리)
            pass

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """ WebSocket 연결 처리 """
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info("GUI 클라이언트 연결됨.")
    await send_log_to_clients("백엔드 서버에 연결되었습니다.", "info")
    try:
        while True:
            # (클라이언트로부터 메시지 수신 대기 - 현재는 사용 안 함)
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info("GUI 클라이언트 연결 끊김.")


# --- [신규] API 엔드포인트: API 키 설정 ---
class ApiKeys(BaseModel):
    access_key: str
    secret_key: str

@app.post("/api/set-keys")
async def set_api_keys(keys: ApiKeys):
    """
    GUI로부터 API 키를 받아 메모리에 저장하고 인증합니다.
    """
    if not keys.access_key or not keys.secret_key:
        raise HTTPException(status_code=400, detail="API keys cannot be empty")
        
    try:
        # 키를 사용하여 임시 Exchange 객체 생성 및 인증 테스트
        test_exchange = UpbitExchange(keys.access_key, keys.secret_key)
        # (get_balance는 private API 호출)
        krw_balance = await test_exchange.get_balance("KRW")
        
        if krw_balance is not None:
            # 인증 성공 시에만 글로벌 변수에 저장
            api_keys["access"] = keys.access_key
            api_keys["secret"] = keys.secret_key
            
            success_msg = f"API 키 저장 및 인증 성공. (보유 KRW: {krw_balance:,.0f} 원)"
            logger.info(success_msg)
            await send_log_to_clients(success_msg, "success")
            return {"status": "success", "message": "API keys set and verified", "balance_krw": krw_balance}
        else:
            raise Exception("Failed to get balance (None returned)")
            
    except Exception as e:
        # 인증 실패
        logger.warning(f"API 키 인증 실패: {e}")
        api_keys["access"] = None # 키 초기화
        api_keys["secret"] = None
        error_msg = f"API 키 인증 실패: {str(e)}"
        await send_log_to_clients(error_msg, "error")
        # (pyupbit은 오류 메시지를 상세히 반환하므로 detail에 포함)
        raise HTTPException(status_code=401, detail=error_msg)


# --- API 엔드포인트: 전체 마켓 목록 ---
@app.get("/api/markets")
async def get_all_markets():
    """ 업비트 KRW 마켓 목록 반환 (공용 API) """
    try:
        # [수정] 키가 없는 'public_exchange' 인스턴스 사용
        markets = await public_exchange.get_market_all()
        if not markets:
             raise HTTPException(status_code=404, detail="Markets not found")
        return markets
    except Exception as e:
        logger.error(f"마켓 목록 로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- API 엔드포인트: 봇 시작 ---
@app.post("/api/start")
async def start_bots(symbols: List[str]):
    """ 선택된 심볼(코인)들에 대한 자동매매 봇 태스크 시작 """
    started_bots = []
    
    # [신규] 봇 시작 전 API 키 설정 여부 확인
    if not api_keys["access"] or not api_keys["secret"]:
        msg = "봇 시작 실패: API 키가 설정되지 않았습니다. GUI에서 먼저 키를 저장하세요."
        logger.warning(msg)
        await send_log_to_clients(msg, "error")
        return {"status": "error", "message": msg, "started": []}

    for symbol in symbols:
        if symbol not in active_bots:
            logger.info(f"[{symbol}] 봇 시작 명령 수신.")
            await send_log_to_clients(f"[{symbol}] 봇 시작 중...", "info")
            
            # 비동기 태스크(trading_bot_task) 생성 및 실행
            task = asyncio.create_task(trading_bot_task(symbol))
            active_bots[symbol] = task
            started_bots.append(symbol)
        else:
            logger.warning(f"[{symbol}] 봇이 이미 실행 중입니다.")
            await send_log_to_clients(f"[{symbol}] 봇이 이미 실행 중입니다.", "warn")
            
    return {"status": "success", "message": f"{len(started_bots)} bots started.", "started": started_bots}


# --- API 엔드포인트: 봇 중지 ---
@app.post("/api/stop")
async def stop_bots(symbols: List[str]):
    """ 선택된 심볼(코인)들에 대한 자동매매 봇 태스크 중지 """
    stopped_bots = []
    for symbol in symbols:
        task = active_bots.pop(symbol, None) # 딕셔너리에서 제거
        if task:
            try:
                task.cancel() # 태스크 취소
                await task # 태스크가 완전히 종료될 때까지 대기
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"[{symbol}] 봇 중지 중 오류: {e}")
                
            logger.info(f"[{symbol}] 봇이 중지되었습니다.")
            await send_log_to_clients(f"[{symbol}] 봇이 중지되었습니다.", "info")
            stopped_bots.append(symbol)
        else:
            logger.warning(f"[{symbol}] 봇이 실행 중이지 않습니다.")
            await send_log_to_clients(f"[{symbol}] 봇이 실행 중이지 않습니다.", "warn")

    return {"status": "success", "message": f"{len(stopped_bots)} bots stopped.", "stopped": stopped_bots}


# --- 자동매매 핵심 로직 (개별 봇 태스크) ---
async def trading_bot_task(symbol: str):
    """
    개별 코인(심볼)에 대한 v3.5 전략 기반 자동매매 비동기 태스크
    """
    
    # --- [신규] 봇 시작 시 API 키 재확인 ---
    if not api_keys["access"] or not api_keys["secret"]:
        msg = f"[{symbol}] API 키가 설정되지 않아 봇을 시작할 수 없습니다."
        logger.error(msg)
        await send_log_to_clients(msg, "error")
        active_bots.pop(symbol, None) # (혹시 모르니 다시 제거)
        return
    
    # --- [수정] 봇 모듈 초기화 (메모리에 저장된 API 키 사용) ---
    try:
        # (주의) 이 객체들은 봇이 실행되는 동안 메모리에 유지됨
        
        # [수정] 봇 전용 'private_exchange' 생성 (키 전달)
        private_exchange = UpbitExchange(
            access_key=api_keys["access"], 
            secret_key=api_keys["secret"]
        )
        
        # [수정] private_exchange를 사용하는 DataManager 생성
        data_manager = DataManager(private_exchange)
        
        # (임시) 총 자본금 100만원, 1회 거래 리스크 0.5% (5,000원)
        # TODO: 이 설정도 GUI에서 입력받도록 수정 필요
        risk_manager = RiskManager(total_capital=1_000_000, base_risk_per_trade_pct=0.5)
        
        # [수정] data_manager가 private_exchange를 참조
        signal_engine = SignalEngine(data_manager, db, symbol)
        
        # [수정] private_exchange 전달
        position_manager = PositionManager(private_exchange, db, risk_manager, symbol)
        
        await send_log_to_clients(f"[{symbol}] 봇 초기화 완료 (전략: v3.5).", "success")

    except Exception as e:
        logger.critical(f"[{symbol}] 봇 초기화 실패: {e}")
        await send_log_to_clients(f"[{symbol}] 봇 초기화 실패: {e}", "error")
        active_bots.pop(symbol, None)
        return

    # --- 봇 메인 루프 (Loop) ---
    while True:
        try:
            # (태스크 취소 감지 지점 1)
            await asyncio.sleep(1) 
            
            # --- 1. 현재 가격 확인 ---
            current_price = await data_manager.get_current_price(symbol)
            if current_price == 0.0:
                await send_log_to_clients(f"[{symbol}] 현재 가격 조회 실패. (루프 건너뜀)", "warn")
                await asyncio.sleep(30) # (오류 시 30초 대기)
                continue

            # --- 2. 포지션 관리 (손절/익절 확인) ---
            if position_manager.has_position():
                await position_manager.update_positions(current_price)
                # (포지션 보유 중에는 신규 진입 신호 체크 안 함)
                await asyncio.sleep(10) # (포지션 보유 시 10초마다 가격 체크)
                continue

            # --- 3. 신규 신호 확인 ---
            # (포지션이 없을 때만 실행)
            
            # (v3.5는 H1(1시간봉) 기준)
            # TODO: 현재는 매 루프마다 H1 데이터를 새로 가져옴
            # (개선: 1시간에 1번만 가져오도록 최적화 필요)
            df_h1 = await data_manager.fetch_ohlcv(symbol, 'minutes60', 200)
            
            if df_h1.empty:
                await send_log_to_clients(f"[{symbol}] H1 데이터 로드 실패. (루프 건너뜀)", "warn")
                await asyncio.sleep(60) # (데이터 오류 시 1분 대기)
                continue

            # (태스크 취소 감지 지점 2)
            await asyncio.sleep(1)

            # --- 4. v3.5 전략 실행 (1, 2, 3단계) ---
            signal_dict = signal_engine.generate_signal_v3_5(df_h1)

            if signal_dict:
                # (신호 발생!)
                await send_log_to_clients(f"[{symbol}] 신호 감지 (점수: {signal_dict['score']}). 리스크 계산 시작...", "info")
                
                # --- 5. 리스크 계산 (v3.5 4단계) ---
                final_signal = risk_manager.calculate_position_v3_5(signal_dict, current_price)
                
                if final_signal:
                    # (최종 진입 결정)
                    await send_log_to_clients(f"[{symbol}] 최종 진입 결정. (총 {final_signal.total_position_size_krw:,.0f} KRW)", "success")
                    
                    # --- 6. 포지션 진입 (v3.5 4단계 실행) ---
                    await position_manager.enter_position(final_signal)
                    
                    # (진입 후 1시간 대기 - 중복 진입 방지)
                    await send_log_to_clients(f"[{symbol}] 신규 진입 완료. 1시간 동안 대기합니다.", "info")
                    await asyncio.sleep(3600) 
                
            # (신호 없음)
            # await send_log_to_clients(f"[{symbol}] 신호 없음. (대기)", "debug")
            
            # --- 7. 루프 대기 (v3.5는 1시간봉 기준) ---
            # (임시) 1분마다 신호를 체크
            # (개선 필요: H1 캔들이 완성될 때(매 정시)만 체크하도록)
            await asyncio.sleep(60) 

        except asyncio.CancelledError:
            # (봇 중지 명령 수신)
            logger.info(f"[{symbol}] 봇 태스크 취소됨 (정상 중지).")
            # (필요시, 중지 직전 포지션 정리 로직 추가)
            # await position_manager.close_position(reason="BotStopped")
            break # 루프 탈출
            
        except Exception as e:
            # (메인 루프 오류)
            logger.error(f"[{symbol}] 봇 메인 루프 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await send_log_to_clients(f"[{symbol}] 봇 실행 중 심각한 오류 발생: {e}", "error")
            await asyncio.sleep(60) # (오류 발생 시 1분 대기 후 재시도)


# --- (개발용) React 빌드 파일 서빙 ---
# (주: uvicorn으로 FastAPI 실행 시, React는 npm start로 별도 실행 권장)
# (만약 npm run build 후 FastAPI로만 서빙하려면 아래 주석 해제)
# app.mount("/", StaticFiles(directory="frontend/build", html=True), name="static")

# --- 서버 실행 (python main.py 로 실행 시) ---
if __name__ == "__main__":
    logger.info("Athena v1 백엔드 서버를 시작합니다...")
    logger.info(" (주의: React GUI는 'frontend' 폴더에서 'npm start'로 별도 실행해야 합니다.)")
    
    # (uvicorn --reload 옵션 대신 수동 실행)
    uvicorn.run(app, host="127.0.0.1", port=8000)