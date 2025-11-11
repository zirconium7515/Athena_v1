// Athena_v1/frontend/src/App.js
// [수정] 2024.11.11 - 레이아웃 충돌 해결 (className 수정)
// [수정] 2024.11.11 - (요청 2) 코인 목록 접기/펴기 기능 추가

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  
  // --- State 관리 ---
  
  // 0. API 키
  const [accessKey, setAccessKey] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [apiKeyStatus, setApiKeyStatus] = useState({ message: '', type: 'info' });

  // 1. 코인 목록
  const [allMarkets, setAllMarkets] = useState([]); // 업비트 전체 KRW 마켓
  const [searchQuery, setSearchQuery] = useState(''); // 검색어
  const [selectedMarkets, setSelectedMarkets] = useState(new Set()); // 사용자가 선택한 마켓
  const [isCoinListOpen, setIsCoinListOpen] = useState(true); // (요청 2: 코인 목록 토글 state)

  // 2. 봇 상태
  const [runningBots, setRunningBots] = useState(new Set()); // 현재 실행 중인 봇
  
  // 3. 로그
  const [logs, setLogs] = useState([]); // 로그 메시지 배열
  const logsEndRef = useRef(null); // (로그 자동 스크롤 참조)

  // --- WebSocket (로그 수신) ---
  useEffect(() => {
    // (WebSocket 연결은 컴포넌트 마운트 시 1회만 실행)
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      // (로그 레벨 'info'는 CSS 클래스 이름)
      addLogMessage('로그 서버(WebSocket)에 연결되었습니다.', 'info');
    };

    ws.onmessage = (event) => {
      try {
        const logEntry = JSON.parse(event.data);
        addLogMessage(logEntry.message, logEntry.level);
      } catch (error) {
        addLogMessage('수신한 로그를 파싱하는 데 실패했습니다.', 'error');
      }
    };

    ws.onclose = () => {
      addLogMessage('로그 서버(WebSocket) 연결이 끊겼습니다.', 'error');
    };

    ws.onerror = (error) => {
      addLogMessage('로그 서버(WebSocket) 오류 발생.', 'error');
    };

    // (컴포넌트 언마운트 시 WebSocket 연결 정리)
    return () => {
      ws.close();
    };
    // (의존성 배열이 비어있음 [] -> 마운트 시 1회만 실행)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- 코인 목록 (API) ---
  useEffect(() => {
    // (코인 목록은 컴포넌트 마운트 시 1회만 로드)
    const fetchMarkets = async () => {
      try {
        const response = await axios.get('/api/markets');
        setAllMarkets(response.data);
        addLogMessage(`업비트 KRW 마켓 ${response.data.length}개 목록 로드 성공.`, 'info');
      } catch (error) {
        let errorMsg = '업비트 마켓 목록 로드 실패.';
        if (error.response && error.response.status === 404) {
          errorMsg = '업비트 마켓 목록 로드 실패 (404). 백엔드 실행 및 프록시 설정을 확인하세요.';
        }
        addLogMessage(errorMsg, 'error');
        console.error("Market fetch error:", error);
      }
    };

    fetchMarkets();
    // (의존성 배열이 비어있음 [] -> 마운트 시 1회만 실행)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- 로그 자동 스크롤 ---
  useEffect(() => {
    // (logs 상태가 변경될 때마다 실행)
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // --- 유틸리티 함수 ---
  const addLogMessage = (message, level = 'info') => {
    // (로그는 500개까지만 유지)
    setLogs((prevLogs) => [
      ...prevLogs.slice(-499), 
      { timestamp: new Date().toISOString(), message, level }
    ]);
  };

  // --- 이벤트 핸들러 ---
  
  // (API 키 저장 버튼 클릭)
  const handleSetApiKeys = async () => {
    if (!accessKey || !secretKey) {
      setApiKeyStatus({ message: 'Access Key와 Secret Key를 모두 입력해야 합니다.', type: 'error' });
      return;
    }
    
    setApiKeyStatus({ message: 'API 키 인증 중...', type: 'info' });

    try {
      const response = await axios.post('/api/set-keys', {
        access_key: accessKey,
        secret_key: secretKey,
      });
      // (백엔드가 성공(200 OK)을 반환하면)
      const successMsg = response.data.message || 'API 키 저장 및 인증 성공.';
      setApiKeyStatus({ message: successMsg, type: 'success' });
      
    } catch (error) {
      // (백엔드가 401(인증 실패) 또는 500(서버 오류)을 반환하면)
      let errorMsg = 'API 키 인증 실패.';
      if (error.response && error.response.data && error.response.data.detail) {
        errorMsg = error.response.data.detail;
      }
      setApiKeyStatus({ message: errorMsg, type: 'error' });
    }
  };

  // (코인 목록 검색)
  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
  };

  // (코인 목록에서 코인 클릭)
  const handleMarketClick = (marketSymbol) => {
    const newSelection = new Set(selectedMarkets);
    if (newSelection.has(marketSymbol)) {
      newSelection.delete(marketSymbol);
    } else {
      newSelection.add(marketSymbol);
    }
    setSelectedMarkets(newSelection);
  };
  
  // (봇 시작 버튼 클릭)
  const handleStartBots = async () => {
    // (선택된 코인 중, 아직 실행되지 않은 코인만 필터링)
    const botsToStart = Array.from(selectedMarkets).filter(
      (symbol) => !runningBots.has(symbol)
    );

    if (botsToStart.length === 0) {
      addLogMessage('선택된 코인 중 새로 시작할 봇이 없습니다.', 'warn');
      return;
    }

    try {
      addLogMessage(`[${botsToStart.join(', ')}] 봇 시작 요청...`, 'info');
      const response = await axios.post('/api/start', botsToStart);
      
      // (백엔드가 성공적으로 시작한 봇 목록)
      const started = response.data.started || [];
      setRunningBots(new Set([...runningBots, ...started]));
      
      if (started.length > 0) {
        addLogMessage(`[${started.join(', ')}] 봇이 성공적으로 시작되었습니다.`, 'success');
      }

    } catch (error) {
      let errorMsg = '봇 시작 실패.';
      if (error.response && error.response.data && error.response.data.message) {
        errorMsg = error.response.data.message;
      }
      addLogMessage(errorMsg, 'error');
    }
  };

  // (봇 중지 버튼 클릭)
  const handleStopBots = async () => {
    // (선택된 코인 중, 현재 실행 중인 코인만 필터링)
     const botsToStop = Array.from(selectedMarkets).filter(
      (symbol) => runningBots.has(symbol)
    );

    if (botsToStop.length === 0) {
      addLogMessage('선택된 코인 중 중지할 봇이 없습니다.', 'warn');
      return;
    }

    try {
      addLogMessage(`[${botsToStop.join(', ')}] 봇 중지 요청...`, 'info');
      const response = await axios.post('/api/stop', botsToStop);
      
      // (백엔드가 성공적으로 중지한 봇 목록)
      const stopped = response.data.stopped || [];
      const newRunningBots = new Set(runningBots);
      stopped.forEach(symbol => newRunningBots.delete(symbol));
      setRunningBots(newRunningBots);

      if (stopped.length > 0) {
        addLogMessage(`[${stopped.join(', ')}] 봇이 성공적으로 중지되었습니다.`, 'info');
      }

    } catch (error) {
      addLogMessage('봇 중지 실패.', 'error');
    }
  };

  // --- 렌더링 ---
  
  // (검색어에 따라 코인 목록 필터링)
  const filteredMarkets = allMarkets.filter(
    (market) =>
      market.korean_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      market.market.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="App">
      <header className="App-header">
        <h1>Athena v1 - 자동매매 프로그램</h1>
      </header>
      
      <main className="main-content">
        
        {/* --- 왼쪽: 제어판 --- */}
        <div className="control-panel">
          
          {/* --- 0. API 키 설정 --- */}
          <div className="api-keys-section">
            <h2>0. API 키 설정</h2>
            <p>봇을 실행하기 전에 API 키를 저장해야 합니다.</p>
            <input
              type="text"
              placeholder="Upbit Access Key"
              value={accessKey}
              onChange={(e) => setAccessKey(e.target.value)}
              className="api-input"
            />
            <input
              type="password"
              placeholder="Upbit Secret Key"
              value={secretKey}
              onChange={(e) => setSecretKey(e.target.value)}
              className="api-input"
            />
            <button onClick={handleSetApiKeys} className="api-button">
              API 키 저장
            </button>
            {apiKeyStatus.message && (
              <div className={`api-status ${apiKeyStatus.type}`}>
                {apiKeyStatus.message}
              </div>
            )}
          </div>
          
          {/* --- 1. 코인 선택 (요청 2: 수정) --- */}
          <div className="market-selector">
            
            {/* (클릭 가능한 헤더) */}
            <div 
              className="collapsible-header" 
              onClick={() => setIsCoinListOpen(!isCoinListOpen)}
            >
              <h2>1. 거래 코인 선택</h2>
              {/* (토글 아이콘) */}
              <span className="toggle-icon">{isCoinListOpen ? '▲ 숨기기' : '▼ 펼치기'}</span>
            </div>
            
            {/* (isCoinListOpen이 true일 때만 내용 표시) */}
            {isCoinListOpen && (
              <div className="market-list-content">
                <input
                  type="text"
                  placeholder="코인 이름 또는 심볼 검색..."
                  className="search-bar"
                  value={searchQuery}
                  onChange={handleSearchChange}
                />
                <div className="market-list">
                  {filteredMarkets.length > 0 ? (
                    filteredMarkets.map((market) => (
                      <div
                        key={market.market}
                        className={`market-item ${selectedMarkets.has(market.market) ? 'selected' : ''}`}
                        onClick={() => handleMarketClick(market.market)}
                      >
                        <span className="market-name">{market.korean_name}</span>
                        <span className="market-symbol">{market.market}</span>
                        {runningBots.has(market.market) && (
                          <span className="status-indicator"> (실행중)</span>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="loading-text">
                      {allMarkets.length === 0 ? "코인 목록 로딩 중..." : "검색 결과 없음"}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {/* --- 2. 봇 제어 --- */}
          <div className="bot-controls">
            <h2>2. 봇 제어</h2>
            <div className="button-group">
              <button onClick={handleStartBots} className="control-button start">
                선택 봇 시작
              </button>
              <button onClick={handleStopBots} className="control-button stop">
                선택 봇 중지
              </button>
            </div>
          </div>
        </div>
        
        {/* --- 오른쪽: 로그 --- */}
        <div className="log-viewer">
          <h2>3. 실시간 로그</h2>
          <div className="log-output">
            {logs.map((log, index) => (
              <div key={index} className={`log-entry ${log.level}`}>
                <span className="log-timestamp">
                  [{new Date(log.timestamp).toLocaleTimeString()}]
                </span>
                <span className="log-message">{log.message}</span>
              </div>
            ))}
            {/* (자동 스크롤을 위한 빈 div) */}
            <div ref={logsEndRef} />
          </div>
        </div>
        
      </main>
    </div>
  );
}

export default App;