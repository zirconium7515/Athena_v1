# Athena_v1/main.py
# [수정] 2024.11.11 - (요청) GUI에서 API 키 입력
# [수정] 2024.11.11 - (요청) 차트 데이터용 /api/ohlcv 엔드포인트 신설
# [수정] 2024.11.11 - (오류) SyntaxError: invalid syntax (// 주석 수정)
# [수정] 2024.11.11 - (오류) NameError: 'pd' is not defined (pandas 임포트 추가)
# [수정] 2024.11.11 - (오류) trading_bot_task v3.5 로직 호출 오류 수정
# [수정] 2024.11.11 - (오류) TypeError: __init__ got unexpected keyword 'exchange'
# [수정] 2024.11.11 - (요청) 차트 실시간 갱신 (Upbit WebSocket Ticker) 추가
# [수정] 2024.11.11 - (리팩토링) WebSocket 메시지 포맷 표준화 (type, payload)
# [수정] 2024.11.11 - (요청) 차트 2단계: 다중 차트 구독 (Ticker Set)
# [수정] 2024.11.11 - (오류) InsufficientFundsBid Race Condition 해결 (asyncio.Lock)
# [수정] 2024.11.11 - (오류) pyupbit 캐시 문제 해결 (Private Exchange 공유 객체)
# [수정] 2024.11.11 - (요청) /api/set-keys가 KRW + 코인 자산 요약(List)을 반환
# [수정] 2024.11.12 - (오류) AttributeError: module 'uuid' has no attribute 'v4' (uuid.uuid4()로 수정)
# [수정] 2024.11.12 - (요청) 모의 투자 (MockExchange) 기능 추가
# [수정] 2024.11.12 - (요청) 자산 요약(수량) 갱신을 위한 /api/account-summary 엔드포인트 신설

import sys
import os
import asyncio
import pandas as pd 
import json 
import websockets 
import uuid 
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Set, Any 
from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- 경로 설정 (중요) ---
current_file_path = os.path.abspath(__file__)
project_root_dir = os.path.dirname(current_file_path)
if project_root_dir not in sys.path:
    sys.path.append(project_root_dir)
# --- 경로 설정 끝 ---

# --- 모듈 임포트 ---
from config import LOG_FILE_PATH, DB_FILE_PATH, LOG_LEVEL
from ai_trader.utils.logger import setup_logger
from ai_trader.exchange_api import UpbitExchange
from ai_trader.mock_exchange import MockExchange 
from ai_trader.database import Database
from ai_trader.data_manager import DataManager
from ai_trader.signal_engine import SignalEngineV3_5
from ai_trader.risk_manager import RiskManager
from ai_trader.position_manager import PositionManager

# --- 전역 변수 및 설정 ---

# 로거 설정
logger = setup_logger("MainApp", LOG_FILE_PATH, LOG_LEVEL)

# API 키 저장소
api_keys_store: Dict[str, Optional[str]] = {
    "access_key": None,
    "secret_key": None
}

# 공용 API (Public - 키 없음)
public_exchange = UpbitExchange(access_key=None, secret_key=None)
# 봇/잔고용 API (Private)
private_exchange: Optional[UpbitExchange | MockExchange] = None 

# 봇 관리 딕셔너리
active_bots: Dict[str, asyncio.Task] = {}

# 자본 접근 동기화를 위한 Lock
capital_lock = asyncio.Lock()

# 업비트 틱(Ticker) WebSocket 관리
upbit_ws_task: Optional[asyncio.Task] = None
upbit_ws_client: Optional[websockets.WebSocketClientProtocol] = None
current_ticker_symbols: Set[str] = {"KRW-BTC"} 

# WebSocket 연결 관리 (GUI 클라이언트)
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"새 WebSocket 연결: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket 연결 해제: {websocket.client}")
        
        if len(self.active_connections) == 0:
            logger.info("모든 GUI 클라이언트 연결 해제. 업비트 Ticker WebSocket 종료 중...")
            global upbit_ws_task, upbit_ws_client
            if upbit_ws_task:
                upbit_ws_task.cancel()
                upbit_ws_task = None
            if upbit_ws_client:
                logger.info("업비트 Ticker 태스크 취소됨.")
                pass

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"WebSocket 전송 오류: {e}")

manager = ConnectionManager()

# --- 업비트 실시간 Ticker WebSocket 클라이언트 ---

async def start_upbit_ticker_ws(symbols: List[str]):
    global upbit_ws_client, manager, current_ticker_symbols
    
    current_ticker_symbols = set(symbols) 
    if not symbols:
        logger.warning("업비트 Ticker WS: 구독할 심볼이 없습니다. 연결을 시작하지 않습니다.")
        return
        
    uri = "wss://api.upbit.com/websocket/v1"
    
    try:
        async with websockets.connect(uri) as ws:
            upbit_ws_client = ws 
            
            subscribe_msg = json.dumps([
                {"ticket": f"athena-chart-{uuid.uuid4()}"}, 
                {"type": "ticker", "codes": symbols} 
            ])
            await ws.send(subscribe_msg)
            logger.info(f"업비트 Ticker WebSocket 연결 성공. [{', '.join(symbols)}] 구독 시작.")
            
            async for message in ws:
                if isinstance(message, bytes):
                    try:
                        data = json.loads(message.decode('utf-8'))
                        await manager.broadcast({
                            "type": "tick",
                            "payload": data
                        })
                    except json.JSONDecodeError:
                        logger.warning("업비트 Ticker WS: JSON 디코딩 실패")
                    except Exception as e:
                        logger.error(f"업비트 Ticker WS: 틱 처리 중 오류: {e}")

    except asyncio.CancelledError:
        logger.info(f"업비트 Ticker WS [{', '.join(symbols)}] 작업이 취소되었습니다 (심볼 변경 또는 서버 종료).")
    except websockets.exceptions.ConnectionClosed as e:
        logger.warning(f"업비트 Ticker WS [{', '.join(symbols)}] 연결 끊김 (재시도 필요): {e}")
    except Exception as e:
        logger.error(f"업비트 Ticker WS [{', '.join(symbols)}] 치명적 오류: {e}", exc_info=True)
    finally:
        upbit_ws_client = None
        logger.info(f"업비트 Ticker WS [{', '.join(symbols)}] 연결 종료.")


# --- FastAPI 수명 주기 (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- Athena v1 (FastAPI) 서버 시작 ---")
    try:
        db = Database(db_path=DB_FILE_PATH)
        db.create_tables() 
        logger.info(f"데이터베이스 초기화 성공: {DB_FILE_PATH}")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
    
    global upbit_ws_task
    if upbit_ws_task is None:
        upbit_ws_task = asyncio.create_task(start_upbit_ticker_ws(list(current_ticker_symbols)))
    
    yield 
    
    logger.info("--- Athena v1 (FastAPI) 서버 종료 중 ---")
    
    if upbit_ws_task:
        upbit_ws_task.cancel()
        await upbit_ws_task
        
    if active_bots:
        logger.info(f"실행 중인 {len(active_bots)}개의 봇을 모두 중지합니다...")
        tasks = []
        for symbol, task in active_bots.items():
            task.cancel()
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("모든 봇이 중지되었습니다.")
    
    await UpbitExchange.close_session()
    logger.info("aiohttp 클라이언트 세션 종료.")


# --- FastAPI 앱 초기화 ---
app = FastAPI(
    title="Athena v1 Trading Bot API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- API 모델 (Pydantic) ---

class ApiKeyModel(BaseModel):
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    is_mock_trade: bool 

class BotControlModel(BaseModel):
    symbols: List[str]
    
class ChartSubscribeListModel(BaseModel):
    type: str # "subscribe_charts_list"
    symbols: List[str]

# --- [신규] (요청) 자산 요약 헬퍼 함수 ---
async def _get_account_summary(exchange: UpbitExchange | MockExchange) -> Dict[str, Any]:
    """
    (신규) exchange 객체에서 전체 자산 목록(수량)을 가져오고,
    public_exchange를 이용해 현재가와 평가액을 계산하여 반환합니다.
    """
    global public_exchange
    
    # 1. 자산 수량 조회 (Private API)
    all_balances_raw = await exchange.get_balance(ticker=None, verbose=True, use_cache=False)
    
    if not all_balances_raw or (isinstance(all_balances_raw, dict) and 'error' in all_balances_raw):
        error_msg = all_balances_raw.get('error', '자산 목록(수량)을 불러오지 못했습니다.') if isinstance(all_balances_raw, dict) else "자산 목록 조회 실패 (None)"
        raise Exception(error_msg)

    # 2. 자산 요약 리스트 생성
    account_summary = []
    tickers_to_fetch_price = []
    total_assets_krw = 0.0

    for asset in all_balances_raw:
        balance = float(asset.get('balance', 0.0))
        
        if asset['currency'] == "KRW":
            account_summary.append({
                "currency": "KRW",
                "name": "원화",
                "balance": balance,
                "avg_buy_price": 1.0,
                "value_krw": balance
            })
            total_assets_krw += balance
        
        # (1원 이상의 가치를 가진 코인만)
        elif balance * float(asset.get('avg_buy_price', 0.0)) > 1.0:
            tickers_to_fetch_price.append(f"KRW-{asset['currency']}")
            account_summary.append({
                "currency": asset['currency'],
                "name": f"KRW-{asset['currency']}", 
                "balance": balance,
                "avg_buy_price": float(asset.get('avg_buy_price', 0.0)),
                "value_krw": 0.0 
            })

    # 3. 코인 현재가 조회 (Public API)
    if tickers_to_fetch_price:
        current_prices = await public_exchange.get_current_price(tickers_to_fetch_price)
        all_markets_map = {m['market']: m['korean_name'] for m in await public_exchange.get_market_all()}

        for asset in account_summary:
            if asset['currency'] == 'KRW':
                continue
            
            ticker = f"KRW-{asset['currency']}"
            asset['name'] = all_markets_map.get(ticker, asset['currency']) 
            
            # (get_current_price가 float을 반환한 경우 예외 처리)
            current_price = 0.0
            if isinstance(current_prices, dict):
                 current_price = current_prices.get(ticker, 0.0)
            elif isinstance(current_prices, float) and len(tickers_to_fetch_price) == 1:
                 current_price = current_prices
            
            asset['value_krw'] = asset['balance'] * current_price
            total_assets_krw += asset['value_krw']
    
    return {"total_assets_krw": total_assets_krw, "account_summary": account_summary}

# --- API 엔드포인트 (HTTP) ---

@app.post("/api/set-keys")
async def set_api_keys(keys: ApiKeyModel):
    logger.info("API 키/모드 설정 요청 수신...")
    
    global private_exchange
    
    try:
        # 1. 모의 투자 모드
        if keys.is_mock_trade:
            logger.info("--- 모의 투자 모드 활성화 ---")
            private_exchange = MockExchange()
            success_msg = f"모의 투자 모드 활성화. (가상 자본금: {private_exchange.STARTING_CAPITAL_KRW:,.0f}원)"
            
        # 2. 실전 매매 모드
        else:
            logger.info("--- 실전 매매 모드 활성화 ---")
            if not keys.access_key or not keys.secret_key:
                raise Exception("실전 매매 모드에서는 API 키가 반드시 필요합니다.")
            
            exchange = UpbitExchange(keys.access_key, keys.secret_key)
            
            # (인증 테스트 - get_balance_no_cache를 호출)
            test_balance = await exchange.get_balance(ticker="KRW", verbose=True, use_cache=False)
            if not test_balance or (isinstance(test_balance, dict) and 'error' in test_balance):
                error_msg = test_balance.get('error', 'API 키 인증 실패') if isinstance(test_balance, dict) else "API 키 인증 실패"
                raise Exception(error_msg)

            # (인증 성공)
            api_keys_store["access_key"] = keys.access_key
            api_keys_store["secret_key"] = keys.secret_key
            private_exchange = exchange 
            success_msg = "실전 매매 API 키 인증 성공."

        # 3. (공통) 자산 요약 불러오기
        summary_data = await _get_account_summary(private_exchange)
        
        final_msg = f"{success_msg} (총 보유자산: {summary_data['total_assets_krw']:,.0f}원)"
        logger.info(final_msg)
        
        await manager.broadcast({
            "type": "log", 
            "payload": {"level": "success", "message": final_msg}
        })
        
        return {"message": final_msg, "account_summary": summary_data['account_summary']}
        
    except Exception as e:
        error_msg = f"API 키 인증/자산 조회 실패: {str(e)}"
        logger.warning(error_msg, exc_info=True)
        private_exchange = None 
        raise HTTPException(status_code=401, detail=error_msg)

# [신규] (요청) 자산 요약(수량) 수동/자동 갱신용
@app.get("/api/account-summary")
async def get_account_summary():
    global private_exchange
    
    if not private_exchange:
        logger.warning("자산 요약 갱신 실패 (모드 미설정)")
        raise HTTPException(status_code=401, detail="API 키 또는 모의 투자 모드가 설정되지 않았습니다.")
        
    try:
        logger.info("자산 요약(수량) 갱신 요청 수신...")
        summary_data = await _get_account_summary(private_exchange)
        return {"account_summary": summary_data['account_summary']}
        
    except Exception as e:
        error_msg = f"자산 요약 갱신 실패: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/markets")
async def get_all_markets():
    try:
        markets = await public_exchange.get_market_all()
        if not markets:
            logger.warning("get_market_all()이 빈 목록을 반환했습니다.")
            raise HTTPException(status_code=404, detail="업비트에서 마켓 목록을 가져오지 못했습니다.")
        return markets
    except Exception as e:
        logger.error(f"마켓 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ohlcv/{symbol}")
async def get_ohlcv_data(symbol: str, interval: str = "minute60", count: int = 200):
    logger.debug(f"차트 데이터 요청: {symbol}, {interval}, {count}")
    try:
        data_manager = DataManager(exchange_api=public_exchange)
        df = await data_manager.fetch_ohlcv(symbol, interval, count)
        
        if df.empty:
            logger.warning(f"OHLCV 데이터 없음: {symbol}, {interval}")
            return []

        df_utc = df.tz_localize('Asia/Seoul').tz_convert('UTC')
        
        df_chart = df_utc[['open', 'high', 'low', 'close']].copy()
        df_chart['time'] = df_utc.index.astype(int) // 10**9 
        
        chart_data = df_chart.reset_index(drop=True).to_dict('records')
        
        return chart_data

    except Exception as e:
        logger.error(f"OHLCV 데이터 조회 실패 ({symbol}, {interval}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OHLCV 데이터 조회 실패: {str(e)}")

@app.post("/api/start")
async def start_bots(control: BotControlModel):
    symbols = control.symbols
    
    global private_exchange
    if not private_exchange: 
        logger.warning("봇 시작 실패: API 키 또는 모의 투자 모드가 설정되지 않았습니다.")
        raise HTTPException(status_code=401, detail="API 키 또는 모의 투자 모드가 설정되지 않았습니다. 0단계에서 먼저 설정을 완료하세요.")

    started = []
    failed = []
    
    for symbol in symbols:
        if symbol not in active_bots:
            try:
                task = asyncio.create_task(
                    trading_bot_task(
                        symbol=symbol,
                        exchange=private_exchange 
                    )
                )
                active_bots[symbol] = task
                started.append(symbol)
                logger.info(f"{symbol} 봇 시작.")
                await manager.broadcast({
                    "type": "log",
                    "payload": {"level": "success", "message": f"{symbol} 봇이 시작되었습니다."}
                })
                
                await asyncio.sleep(0.2) 
                
            except Exception as e:
                logger.error(f"{symbol} 봇 시작 중 예외 발생: {e}", exc_info=True)
                failed.append(symbol)
        else:
            logger.warning(f"{symbol} 봇은 이미 실행 중입니다.")

    return {"status": "success", "started": started, "failed": failed}

@app.post("/api/stop")
async def stop_bots(control: BotControlModel):
    symbols = control.symbols
    stopped = []
    not_found = []

    for symbol in symbols:
        task = active_bots.pop(symbol, None)
        if task:
            try:
                task.cancel()
                await asyncio.sleep(0) 
                stopped.append(symbol)
                logger.info(f"{symbol} 봇 중지 요청.")
                await manager.broadcast({
                    "type": "log",
                    "payload": {"level": "info", "message": f"{symbol} 봇이 중지되었습니다."}
                })
            except Exception as e:
                logger.error(f"{symbol} 봇 중지 중 예외 발생: {e}", exc_info=True)
        else:
            not_found.append(symbol)
            logger.warning(f"{symbol} 봇을 찾을 수 없습니다 (이미 중지됨).")

    return {"status": "success", "stopped": stopped, "not_found": not_found}

@app.get("/api/status")
async def get_status():
    return {"running_bots": list(active_bots.keys())}


# --- WebSocket 엔드포인트 ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    global current_ticker_symbols
    try:
        await websocket.send_json({
            "type": "info",
            "payload": {"message": f"서버 연결 성공. 현재 차트 Ticker: {', '.join(current_ticker_symbols)}"}
        })
    except Exception:
        pass 

    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            
            if data.get("type") == "subscribe_charts_list":
                symbols = data.get("symbols")
                
                if isinstance(symbols, list):
                    logger.info(f"WebSocket 수신: 차트 구독 변경 요청 -> {symbols}")
                    global upbit_ws_task
                    
                    if upbit_ws_task:
                        upbit_ws_task.cancel()
                    
                    upbit_ws_task = asyncio.create_task(start_upbit_ticker_ws(symbols))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}", exc_info=True)
        if websocket in manager.active_connections:
            manager.disconnect(websocket)


# --- 핵심: 개별 봇 비동기 태스크 ---

async def trading_bot_task(symbol: str, exchange: UpbitExchange | MockExchange): 
    
    global capital_lock 
    
    try:
        data_manager = DataManager(exchange)
        db = Database(DB_FILE_PATH)
        
        total_capital_temp = 1000000 
        risk_manager = RiskManager(
            total_capital=total_capital_temp,
            base_risk_per_trade_pct=0.5
        )
        
        position_manager = PositionManager(exchange, db, risk_manager, symbol, manager.broadcast)
        signal_engine = SignalEngineV3_5()
    
    except Exception as e:
        await manager.broadcast({
            "type": "log",
            "payload": {"level": "error", "message": f"[{symbol}] 봇 초기화 실패: {e}"}
        })
        logger.error(f"[{symbol}] 봇 초기화 실패: {e}", exc_info=True)
        return

    try:
        while True:
            df_h1 = await data_manager.fetch_ohlcv(symbol, timeframe="minute60", count=200)
            if df_h1.empty:
                await asyncio.sleep(60)
                continue
            
            current_price = df_h1.iloc[-1]['close']
            current_position = position_manager.get_position(symbol)
            
            if current_position:
                await position_manager.check_exit_conditions(current_position, df_h1.iloc[-1])
            
            if not current_position:
                signal_dict = signal_engine.generate_signal(df_h1, symbol)
                
                if signal_dict and signal_dict.get("score", 0) >= 12:
                    
                    async with capital_lock:
                        logger.info(f"[{symbol}] 자본 Lock 획득. 잔고 확인 및 주문 시작...")
                        try:
                            current_krw_balance = await exchange.get_krw_balance(use_cache=False)
                            
                            final_signal = risk_manager.calculate_position_size(
                                signal_data=signal_dict,
                                current_price=current_price,
                                krw_balance=current_krw_balance 
                            )
                            
                            if final_signal:
                                await position_manager.enter_position(final_signal)
                        
                        except Exception as e:
                            await manager.broadcast({
                                "type": "log",
                                "payload": {"level": "warn", "message": f"[{symbol}] 진입 처리 중 오류 (Lock 내부): {e}"}
                            })
                            logger.warning(f"[{symbol}] 진입 처리 중 오류 (Lock 내부): {e}", exc_info=True)
                        
                        logger.info(f"[{symbol}] 자본 Lock 해제.")
                    
            await asyncio.sleep(60) 

    except asyncio.CancelledError:
        await manager.broadcast({
            "type": "log",
            "payload": {"level": "info", "message": f"[{symbol}] 봇이 외부 요청에 의해 중지되었습니다."}
        })
        logger.info(f"[{symbol}] 봇이 외부 요청에 의해 중지되었습니다.")
    
    except Exception as e:
        await manager.broadcast({
            "type": "log",
            "payload": {"level": "error", "message": f"[{symbol}] 봇 실행 중 치명적 오류: {e}"}
        })
        logger.error(f"[{symbol}] 봇 실행 중 치명적 오류: {e}", exc_info=True)
    
    finally:
        active_bots.pop(symbol, None)
        logger.info(f"[{symbol}] 봇 태스크가 완전히 종료되었습니다.")


# (개발 중: uvicorn main:app --reload 로 실행 시)
if __name__ == "__main__":
    import uvicorn
    logger.info("--- Uvicorn 개발 서버로 직접 실행 ---")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)