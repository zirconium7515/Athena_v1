// Athena_v1/frontend/src/App.js
// [수정] 2024.11.11 - GUI 레이아웃 깨짐 현상 수정 (className 변경)
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [markets, setMarkets] = useState([]); // 전체 코인 목록
  const [selectedMarkets, setSelectedMarkets] = useState(new Set()); // 사용자가 선택한 코인
  const [runningBots, setRunningBots] = useState(new Set()); // 현재 실행 중인 봇
  const [logs, setLogs] = useState([]); // 실시간 로그
  const [searchTerm, setSearchTerm] = useState(''); // 코인 검색어

  // [신규] API 키 상태
  const [accessKey, setAccessKey] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [apiKeyStatus, setApiKeyStatus] = useState('N/A'); // (N/A, OK, Error)

  const logsEndRef = useRef(null); // 로그 스크롤 참조
  const ws = useRef(null); // WebSocket 참조

  // 1. 컴포넌트 마운트 시 실행
  useEffect(() => {
    // 1-1. 전체 코인 목록 불러오기
    fetchMarkets();
    
    // 1-2. WebSocket 연결
    connectWebSocket();

    // 컴포넌트 언마운트 시 WebSocket 연결 해제
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  // 2. 로그 업데이트 시 자동 스크롤
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // 3. (신규) API 키 저장 핸들러
  const handleSetKeys = async () => {
    if (!accessKey || !secretKey) {
      addLog("액세스 키와 시크릿 키를 모두 입력하세요.", "error");
      setApiKeyStatus("Error");
      return;
    }
    try {
      addLog("API 키 저장 및 인증 시도 중...", "info");
      // 백엔드 /api/set-keys 엔드포인트로 키 전송
      const response = await axios.post('/api/set-keys', {
        access_key: accessKey,
        secret_key: secretKey
      });
      
      if (response.data.status === 'success') {
        const balance = response.data.balance_krw || 0;
        addLog(`API 키 인증 성공. (보유 KRW: ${balance.toLocaleString()} 원)`, "success");
        setApiKeyStatus("OK");
      } else {
        throw new Error(response.data.detail || "알 수 없는 오류");
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || "API 키 인증 실패";
      addLog(`API 키 인증 실패: ${errorMsg}`, "error");
      setApiKeyStatus("Error");
    }
  };

  // 4. WebSocket 연결 함수
  const connectWebSocket = () => {
    // WebSocket 주소 (백엔드: 8000번 포트)
    // React 개발서버(3000)가 아니므로 전체 주소를 사용합니다.
    const wsUrl = "ws://localhost:8000/ws";
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      addLog("백엔드 서버와 연결되었습니다 (WebSocket).", "info");
    };

    ws.current.onmessage = (event) => {
      // 백엔드에서 전송된 로그(JSON) 수신
      try {
        const logEntry = JSON.parse(event.data);
        addLog(logEntry.message, logEntry.level);
      } catch (e) {
        addLog(event.data, "info");
      }
    };

    ws.current.onclose = () => {
      addLog("백엔드 서버와 연결이 끊겼습니다. 5초 후 재연결을 시도합니다.", "error");
      // 5초 후 재연결
      setTimeout(connectWebSocket, 5000);
    };

    ws.current.onerror = (error) => {
      addLog("WebSocket 오류 발생. (백엔드 서버 실행 확인 필요)", "error");
      ws.current.close();
    };
  };

  // 5. 로그 추가 함수
  const addLog = (message, level = "info") => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prevLogs => [
      ...prevLogs,
      { timestamp, message, level }
    ]);
  };

  // 6. 업비트 KRW 마켓 목록 불러오기
  const fetchMarkets = async () => {
    try {
      const response = await axios.get('/api/markets');
      setMarkets(response.data || []);
      addLog(`업비트 KRW 마켓 ${response.data.length}개 목록 로드 완료.`, "info");
    } catch (error) {
      addLog("업비트 마켓 목록 로드 실패. 백엔드 실행 확인.", "error");
    }
  };

  // 7. 코인 선택/해제 핸들러
  const handleMarketSelect = (market) => {
    setSelectedMarkets(prevSelected => {
      const newSelected = new Set(prevSelected);
      if (newSelected.has(market)) {
        newSelected.delete(market);
      } else {
        newSelected.add(market);
      }
      return newSelected;
    });
  };

  // 8. 봇 시작 핸들러
  const handleStartBots = async () => {
    const botsToStart = Array.from(selectedMarkets).filter(m => !runningBots.has(m));
    if (botsToStart.length === 0) {
      addLog("시작할 신규 코인이 선택되지 않았거나, 이미 실행 중입니다.", "warn");
      return;
    }
    
    try {
      // 백엔드 /api/start로 시작할 코인 목록 전송
      const response = await axios.post('/api/start', botsToStart);
      
      if (response.data.status === 'success') {
        const started = response.data.started || [];
        setRunningBots(prevRunning => new Set([...prevRunning, ...started]));
        addLog(`[${started.join(', ')}] 봇 시작 요청 성공.`, "success");
      } else {
        addLog(`봇 시작 요청 실패: ${response.data.message}`, "error");
      }
    } catch (error) {
      addLog(`봇 시작 API 오류: ${error.message}`, "error");
    }
    setSelectedMarkets(new Set()); // 선택 해제
  };

  // 9. 봇 중지 핸들러
  const handleStopBots = async () => {
    const botsToStop = Array.from(selectedMarkets).filter(m => runningBots.has(m));
    if (botsToStop.length === 0) {
      addLog("중지할 실행 중인 코인이 선택되지 않았습니다.", "warn");
      return;
    }

    try {
      // 백엔드 /api/stop으로 중지할 코인 목록 전송
      const response = await axios.post('/api/stop', botsToStop);
      
      if (response.data.status === 'success') {
        const stopped = response.data.stopped || [];
        setRunningBots(prevRunning => {
          const newRunning = new Set(prevRunning);
          stopped.forEach(m => newRunning.delete(m));
          return newRunning;
        });
        addLog(`[${stopped.join(', ')}] 봇 중지 요청 성공.`, "success");
      } else {
        addLog(`봇 중지 요청 실패: ${response.data.message}`, "error");
      }
    } catch (error) {
      addLog(`봇 중지 API 오류: ${error.message}`, "error");
    }
    setSelectedMarkets(new Set()); // 선택 해제
  };

  // 10. 전체 선택/해제
  const toggleSelectAll = (select) => {
    if (select) {
      setSelectedMarkets(new Set(filteredMarkets.map(m => m.market)));
    } else {
      setSelectedMarkets(new Set());
    }
  };

  // 11. 코인 목록 필터링 (검색)
  const filteredMarkets = markets.filter(m =>
    m.korean_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.market.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="App">
      <header className="App-header">
        <h1>Athena v1 - 자동매매 프로그램</h1>
      </header>
      
      <div className="main-container">

        {/* [신규] 0. API 키 설정 섹션 */}
        {/* [수정] className을 "api-keys-section"으로 변경 (CSS 충돌 해결) */}
        <div className="api-keys-section">
          <h2>0. API 키 설정 (필수)</h2>
          <div className="api-inputs">
            <input
              type="password"
              placeholder="Upbit Access Key"
              value={accessKey}
              onChange={(e) => setAccessKey(e.target.value)}
            />
            <input
              type="password"
              placeholder="Upbit Secret Key"
              value={secretKey}
              onChange={(e) => setSecretKey(e.target.value)}
            />
          </div>
          <button onClick={handleSetKeys} className="api-save-btn">
            API 키 저장
          </button>
          <span className={`api-status status-${apiKeyStatus.toLowerCase()}`}>
            상태: {apiKeyStatus}
          </span>
        </div>

        {/* 1. 코인 선택 섹션 */}
        <div className="market-list-section">
          <h2>1. 거래 코인 선택</h2>
          <input
            type="text"
            placeholder="코인명 또는 심볼 검색..."
            className="search-bar"
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <div className="market-list-buttons">
            <button onClick={() => toggleSelectAll(true)}>전체 선택</button>
            <button onClick={() => toggleSelectAll(false)}>전체 해제</button>
          </div>
          <div className="market-list">
            {filteredMarkets.map(market => (
              <div
                key={market.market}
                className={`market-item ${selectedMarkets.has(market.market) ? 'selected' : ''}`}
                onClick={() => handleMarketSelect(market.market)}
              >
                <span>{market.korean_name} ({market.market})</span>
                {runningBots.has(market.market) && (
                  <span className="status-badge running">실행중</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 2. 봇 제어 섹션 */}
        <div className="control-section">
          <h2>2. 봇 제어</h2>
          <button onClick={handleStartBots} className="control-btn start-btn">
            선택 봇 시작
          </button>
          <button onClick={handleStopBots} className="control-btn stop-btn">
            선택 봇 중지
          </button>

          {/* 3. 실행 중인 봇 목록 */}
          <h2>3. 실행중인 봇</h2>
          <div className="running-bots">
            {Array.from(runningBots).length > 0 ? (
              Array.from(runningBots).map(market => (
                <span key={market} className="running-bot-item">
                  {market}
                </span>
              ))
            ) : (
              <p>실행 중인 봇이 없습니다.</p>
            )}
          </div>
        </div>

        {/* 4. 실시간 로그 섹션 */}
        <div className="log-section">
          <h2>4. 실시간 로그</h2>
          <div className="log-output">
            {logs.map((log, index) => (
              <p key={index} className={`log-level-${log.level.toLowerCase()}`}>
                <span className="log-timestamp">[{log.timestamp}]</span>
                <span className="log-message">{log.message}</span>
              </p>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;