// Athena_v1/frontend/src/App.js
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

// 백엔드 API 주소 (package.json의 proxy 설정 또는 .env 파일 사용)
// const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
// package.json proxy 설정 (http://localhost:8000)을 사용하므로 /api/... 로 요청
const API_URL = '';

function App() {
  const [allMarkets, setAllMarkets] = useState([]); // 업비트 KRW 마켓 전체 목록
  const [selectedMarkets, setSelectedMarkets] = useState([]); // 사용자가 선택한 마켓
  const [activeBots, setActiveBots] = useState([]); // 현재 실행 중인 봇
  const [logs, setLogs] = useState([]); // 실시간 로그
  const [searchTerm, setSearchTerm] = useState(''); // 코인 검색어
  const [status, setStatus] = useState('disconnected'); // 'disconnected', 'connected', 'error'
  
  const ws = useRef(null); // WebSocket 참조

  // 1. 컴포넌트 마운트 시 실행
  useEffect(() => {
    // 1-1. 업비트 KRW 마켓 목록 불러오기
    fetchMarkets();
    
    // 1-2. 현재 실행 중인 봇 상태 불러오기
    fetchActiveBots();

    // 1-3. WebSocket 연결
    connectWebSocket();

    // 컴포넌트 언마운트 시 WebSocket 연결 해제
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  // 2. 업비트 마켓 목록 조회 함수
  const fetchMarkets = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/markets`);
      if (response.data && response.data.markets) {
        setAllMarkets(response.data.markets);
      }
    } catch (error) {
      console.error("마켓 목록 조회 실패:", error);
      addLog("[오류] 업비트 마켓 목록 조회에 실패했습니다.");
    }
  };
  
  // 3. 현재 활성화된 봇 목록 조회 함수
  const fetchActiveBots = async () => {
     try {
      const response = await axios.get(`${API_URL}/api/status`);
      if (response.data && response.data.active_bots) {
        setActiveBots(response.data.active_bots);
        // 활성화된 봇들을 선택 목록에도 반영 (UI 일관성)
        setSelectedMarkets(response.data.active_bots);
      }
    } catch (error) {
      console.error("활성 봇 상태 조회 실패:", error);
    }
  };

  // 4. WebSocket 연결 함수
  const connectWebSocket = () => {
    // WebSocket 주소 (백엔드 /ws 엔드포인트)
    // (주의: React 개발 서버(3000)가 아닌 백엔드(8000) 주소 기준)
    const wsUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + 
                  (window.location.hostname) + 
                  ':8000/ws'; // (포트 8000 고정)

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log("WebSocket 연결됨");
      setStatus('connected');
    };

    ws.current.onmessage = (event) => {
      // 백엔드에서 broadcast_log(message)로 보낸 메시지
      addLog(event.data);
    };

    ws.current.onclose = () => {
      console.log("WebSocket 연결 끊김. 5초 후 재시도...");
      setStatus('disconnected');
      // 5초 후 재연결 시도
      setTimeout(connectWebSocket, 5000);
    };
    
    ws.current.onerror = (error) => {
      console.error("WebSocket 오류:", error);
      setStatus('error');
      ws.current.close(); // 오류 발생 시 닫고, onclose가 재연결 시도
    };
  };

  // 5. 로그 추가 함수 (최대 100개 유지)
  const addLog = (message) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prevLogs => [`[${timestamp}] ${message}`, ...prevLogs.slice(0, 99)]);
  };

  // 6. 코인 선택/해제 핸들러
  const handleMarketToggle = (market) => {
    // (주의) 이미 실행 중인 봇은 선택 해제할 수 없음 (중지 버튼을 통해서만 가능)
    if (activeBots.includes(market)) {
      addLog(`[알림] ${market} 봇은 이미 실행 중입니다. 중지하려면 '선택 봇 중지' 버튼을 사용하세요.`);
      return;
    }
    
    setSelectedMarkets(prev => 
      prev.includes(market) 
        ? prev.filter(m => m !== market) 
        : [...prev, market]
    );
  };
  
  // 7. 검색어 필터링된 마켓 목록
  const filteredMarkets = allMarkets.filter(market => 
    market.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  // 8. '선택 봇 시작' 버튼 클릭
  const handleStartBots = async () => {
    const botsToStart = selectedMarkets.filter(m => !activeBots.includes(m));
    if (botsToStart.length === 0) {
      addLog("[알림] 이미 모두 실행 중이거나 선택된 코인이 없습니다.");
      return;
    }
    
    addLog(`[요청] ${botsToStart.join(', ')} 봇 시작...`);
    try {
      const response = await axios.post(`${API_URL}/api/start`, botsToStart);
      if (response.data && response.data.bots) {
        // 성공적으로 시작된 봇들을 activeBots 상태에 추가
        setActiveBots(prev => [...prev, ...response.data.bots]);
      }
    } catch (error) {
      console.error("봇 시작 실패:", error);
      addLog(`[오류] 봇 시작 요청 실패: ${error.message}`);
    }
  };
  
  // 9. '선택 봇 중지' 버튼 클릭
  const handleStopBots = async () => {
    // 선택된 마켓 중에서 현재 활성화된 봇들만 필터링
    const botsToStop = selectedMarkets.filter(m => activeBots.includes(m));
    if (botsToStop.length === 0) {
      addLog("[알림] 중지할 대상(활성화된 봇)이 선택되지 않았습니다.");
      return;
    }
    
    addLog(`[요청] ${botsToStop.join(', ')} 봇 중지...`);
    try {
      const response = await axios.post(`${API_URL}/api/stop`, botsToStop);
      if (response.data && response.data.bots) {
        // 성공적으로 중지된 봇들을 activeBots 및 selectedMarkets 상태에서 제거
        setActiveBots(prev => prev.filter(b => !response.data.bots.includes(b)));
        setSelectedMarkets(prev => prev.filter(b => !response.data.bots.includes(b)));
      }
    } catch (error) {
      console.error("봇 중지 실패:", error);
      addLog(`[오류] 봇 중지 요청 실패: ${error.message}`);
    }
  };

  // 10. 전체 선택/해제 (활성화된 봇 제외)
  const handleSelectAll = () => {
    const nonActiveMarkets = allMarkets.filter(m => !activeBots.includes(m));
    setSelectedMarkets([...activeBots, ...nonActiveMarkets]); // 활성 봇 + 나머지 전체
  };
  const handleDeselectAll = () => {
    setSelectedMarkets([...activeBots]); // 활성 봇만 남기고 해제
  };


  return (
    <div className="App">
      <header className="App-header">
        <h1>Athena v1 - 자동매매 (Strategy v3.5)</h1>
        <div className={`status-light ${status}`}></div>
        <span className="status-text">
          {status === 'connected' ? '서버 연결됨' : (status === 'error' ? '연결 오류' : '연결 중...')}
        </span>
      </header>
      
      <main className="App-main">
        {/* --- 왼쪽: 코인 선택 --- */}
        <div className="container container-markets">
          <h2>1. 거래 코인 선택 (KRW 마켓)</h2>
          <div className="market-controls">
            <input 
              type="text"
              placeholder="코인 검색 (예: BTC)"
              className="search-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <div className="select-buttons">
              <button onClick={handleSelectAll}>전체 선택</button>
              <button onClick={handleDeselectAll}>전체 해제</button>
            </div>
          </div>
          
          <div className="market-list">
            {allMarkets.length === 0 && <p>마켓 목록을 불러오는 중...</p>}
            {filteredMarkets.map(market => (
              <div 
                key={market} 
                className={`market-item 
                            ${selectedMarkets.includes(market) ? 'selected' : ''}
                            ${activeBots.includes(market) ? 'active' : ''}`}
                onClick={() => handleMarketToggle(market)}
              >
                {market}
                {activeBots.includes(market) && <span className="active-badge">실행중</span>}
              </div>
            ))}
          </div>
        </div>

        {/* --- 가운데: 제어 및 상태 --- */}
        <div className="container container-control">
          <h2>2. 봇 제어</h2>
          <div className="control-buttons">
            <button className="button-start" onClick={handleStartBots}>
              선택 봇 시작
            </button>
            <button className="button-stop" onClick={handleStopBots}>
              선택 봇 중지
            </button>
          </div>
          
          <h2>3. 실행중인 봇</h2>
          <div className="active-bot-list">
            {activeBots.length === 0 ? (
              <p>(실행 중인 봇이 없습니다)</p>
            ) : (
              activeBots.map(bot => <span key={bot} className="active-bot-item">{bot}</span>)
            )}
          </div>
        </div>

        {/* --- 오른쪽: 실시간 로그 --- */}
        <div className="container container-logs">
          <h2>4. 실시간 로그</h2>
          <div className="log-output">
            {logs.map((log, index) => (
              <div key={index} className="log-item">{log}</div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;