// Athena_v1/frontend/src/App.js
// [수정] 2024.11.11 - (요청) 차트 1단계 및 로그 토글 기능 추가
// [수정] 2024.11.11 - (요청) 새 레이아웃 적용
// [수정] 2024.11.11 - (요청) 차트 자동 갱신 (1분 Polling) 기능 추가
// [수정] 2024.11.11 - (요청) 차트 실시간 갱신 (WebSocket Ticker) 추가
// [수정] 2024.11.11 - (요청) 차트 2단계: 다중 차트 추가/삭제 (+/-)
// [수정] 2024.11.11 - (요청) 1. '모두 선택/해제' 버튼 및 '선택 개수' 추가
// [수정] 2024.11.11 - (요청) API 키 섹션에 '전체 자산 요약(List)' 표시
// [수정] 2024.11.11 - (요청) 자산 요약 갱신을 위해 Ticker 구독 로직 수정
// [수정] 2024.11.11 - (오류) 'useMemo' is not defined (no-undef) 임포트 누락 수정

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'; // [오류 수정] useMemo 임포트
import axios from 'axios';
import './App.css';
import ChartComponent from './ChartComponent'; 

// 2단계: 다중 차트용 헬퍼 컴포넌트
const ChartItem = ({ 
  chart, 
  allMarkets, 
  chartData, 
  chartTheme, 
  realtimeTick, 
  onUpdate, 
  onRemove,
  isFixed 
}) => {
  
  const timeIntervals = [
    { label: '1분', value: 'minute1' },
    { label: '30분', value: 'minute30' },
    { label: '1시간', value: 'minute60' },
    { label: '4시간', value: 'minute240' },
    { label: '일', value: 'day' },
  ];

  // (차트 설정 변경 시: 코인 또는 인터벌)
  const handleSymbolChange = (e) => {
    onUpdate(chart.id, { ...chart, symbol: e.target.value });
  };
  const handleIntervalChange = (interval) => {
    onUpdate(chart.id, { ...chart, interval: interval });
  };

  return (
    <div className="chart-area">
      
      {/* --- 차트 제어판 --- */}
      <div className="chart-controls">
        <div className="chart-symbol-select">
          <label>차트 코인:</label>
          <select 
            value={chart.symbol} 
            onChange={handleSymbolChange}
          >
            {/* [수정] allMarkets가 로드되기 전에 렌더링될 수 있으므로 방어 코드 추가 */}
            {allMarkets && allMarkets.map(market => (
              <option key={market.market} value={market.market}>
                {market.korean_name} ({market.market})
              </option>
            ))}
          </select>
        </div>
        <div className="chart-interval-select">
          {timeIntervals.map(interval => (
            <button
              key={interval.value}
              className={`interval-button ${chart.interval === interval.value ? 'active' : ''}`}
              onClick={() => handleIntervalChange(interval.value)}
            >
              {interval.label}
            </button>
          ))}
        </div>
        {/* (고정 차트가 아닐 때만 'X' 버튼 표시) */}
        {!isFixed && (
          <button 
            className="chart-remove-button" 
            onClick={() => onRemove(chart.id)}
          >
            ✕
          </button>
        )}
      </div>
      
      {/* --- 차트 렌더링 --- */}
      <div className="chart-container">
        {(chartData && chartData.length > 0) ? (
          <ChartComponent 
            symbol={chart.symbol} 
            chartInterval={chart.interval}
            data={chartData} 
            theme={chartTheme} 
            realtimeTick={realtimeTick}
          />
        ) : (
          <div className="chart-status">
            {chart.symbol} ({chart.interval}) 차트 로딩 중...
          </div>
        )}
      </div>

    </div> 
  );
};
// --- (ChartItem 컴포넌트 끝) ---


function App() {
  
  // --- State 관리 ---
  
  // 0. API 키
  const [accessKey, setAccessKey] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [apiKeyStatus, setApiKeyStatus] = useState({ message: '', type: 'info' });
  // [수정] (krwBalance(float) -> accountSummary(Array))
  const [accountSummary, setAccountSummary] = useState([]); 

  // 1. 코인 목록
  const [allMarkets, setAllMarkets] = useState([]); 
  const [searchQuery, setSearchQuery] = useState(''); 
  const [selectedMarkets, setSelectedMarkets] = useState(new Set());
  const [isCoinListOpen, setIsCoinListOpen] = useState(true); 

  // 2. 봇 상태
  const [runningBots, setRunningBots] = useState(new Set()); 
  
  // 3. 로그
  const [logs, setLogs] = useState([]); 
  const logsEndRef = useRef(null); 
  const [isLogOpen, setIsLogOpen] = useState(true);

  // 4. 차트
  const [charts, setCharts] = useState([
    { id: 1, symbol: 'KRW-BTC', interval: 'minute60' } 
  ]);
  const [chartsData, setChartsData] = useState({}); 

  // 5. 실시간 Ticker
  const [realtimeTick, setRealtimeTick] = useState(null); 
  const [tickerPrices, setTickerPrices] = useState({}); // [신규] (자산 평가용)
  const wsRef = useRef(null); 

  // --- 차트 테마 ---
  const lightTheme = {
    backgroundColor: '#ffffff',
    textColor: '#333333',
    gridColor: '#f0f0f0',
    upColor: '#28a745',
    downColor: '#dc3545',
  };
  const [chartTheme, setChartTheme] = useState(lightTheme);


  // --- WebSocket (로그 및 틱 수신) ---
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    wsRef.current = ws; 

    ws.onopen = () => {};

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        
        if (msg.type === 'log') {
          addLogMessage(msg.payload.message, msg.payload.level);
        } 
        else if (msg.type === 'tick') {
          // (차트용)
          setRealtimeTick(msg.payload);
          
          // [신규] (자산 평가용)
          // (수신한 틱의 최신 가격을 tickerPrices 맵(Map)에 저장)
          setTickerPrices(prevPrices => ({
            ...prevPrices,
            [msg.payload.code]: msg.payload.trade_price
          }));
        }
        else if (msg.type === 'info') {
          addLogMessage(msg.payload.message, 'info');
        }

      } catch (error) {
        addLogMessage('수신한 WebSocket 메시지를 파싱하는 데 실패했습니다.', 'error');
      }
    };

    ws.onclose = () => {
      addLogMessage('백엔드 WebSocket 연결이 끊겼습니다. (서버 재시작 필요)', 'error');
    };
    ws.onerror = (error) => {
      addLogMessage('백엔드 WebSocket 오류 발생.', 'error');
    };

    return () => {
      wsRef.current = null;
      ws.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- 코인 목록 (API) ---
  useEffect(() => {
    const fetchMarkets = async () => {
      try {
        const response = await axios.get('/api/markets');
        setAllMarkets(response.data);
        addLogMessage(`업비트 KRW 마켓 ${response.data.length}개 목록 로드 성공.`, 'info');
      } catch (error) {
        addLogMessage('업비트 마켓 목록 로드 실패 (404).', 'error');
        console.error("Market fetch error:", error);
      }
    };
    fetchMarkets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- 차트 데이터 (Polling: 다중 차트 갱신) ---
  const fetchChartData = useCallback(async (chart) => {
    try {
      const response = await axios.get(`/api/ohlcv/${chart.symbol}`, {
        params: {
          interval: chart.interval,
          count: 200 
        }
      });
      
      if (response.data && response.data.length > 0) {
        setChartsData(prevData => ({
          ...prevData,
          [chart.id]: response.data 
        }));
      } else {
        setChartsData(prevData => ({
          ...prevData,
          [chart.id]: []
        }));
      }
    } catch (error) {
      console.error(`Chart data fetch error for ${chart.symbol}:`, error);
      setChartsData(prevData => ({
        ...prevData,
        [chart.id]: [] 
      }));
    }
  }, []); 

  // (1. charts 배열이 변경(추가/삭제/설정 변경)되면, 해당 차트 데이터 즉시 로드)
  useEffect(() => {
    charts.forEach(chart => {
      fetchChartData(chart);
    });
  }, [charts, fetchChartData]);

  // (2. 1분마다 모든 차트 데이터 갱신)
  useEffect(() => {
    const intervalId = setInterval(() => {
      charts.forEach(chart => {
        fetchChartData(chart);
      });
    }, 60000); // 1분
    return () => clearInterval(intervalId); 
  }, [charts, fetchChartData]); 


  // --- [수정] 차트 실시간 구독 (보유 자산 포함) ---
  useEffect(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      
      // (1. 현재 모든 차트의 심볼)
      const chartSymbols = charts.map(c => c.symbol);
      
      // (2. 현재 보유 중인 코인 심볼)
      const heldSymbols = accountSummary
        .filter(asset => asset.currency !== 'KRW')
        .map(asset => `KRW-${asset.currency}`);
        
      // (3. 두 리스트를 합치고 중복 제거)
      const symbolsToSubscribe = Array.from(new Set([...chartSymbols, ...heldSymbols]));
      
      if (symbolsToSubscribe.length > 0) {
        wsRef.current.send(JSON.stringify({
          type: "subscribe_charts_list",
          symbols: symbolsToSubscribe
        }));
      }
      
      setRealtimeTick(null);
    }
  // [수정] (charts 뿐만 아니라 accountSummary가 변경될 때도 재구독)
  }, [charts, accountSummary]); 


  // --- 로그 자동 스크롤 ---
  useEffect(() => {
    if (isLogOpen) { 
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isLogOpen]);

  // --- 유틸리티 함수 ---
  const addLogMessage = (message, level = 'info') => {
    setLogs((prevLogs) => [
      ...prevLogs.slice(-499), 
      { timestamp: new Date().toISOString(), message, level }
    ]);
  };

  // --- 이벤트 핸들러 ---
  
  // [수정] (API 키 저장 버튼 클릭)
  const handleSetApiKeys = async () => {
    if (!accessKey || !secretKey) {
      setApiKeyStatus({ message: 'Access Key와 Secret Key를 모두 입력해야 합니다.', type: 'error' });
      return;
    }
    setApiKeyStatus({ message: 'API 키 인증 중...', type: 'info' });
    setAccountSummary([]); // (인증 시도 시 기존 잔고 숨김)
    
    try {
      const response = await axios.post('/api/set-keys', {
        access_key: accessKey,
        secret_key: secretKey,
      });
      
      const successMsg = response.data.message || 'API 키 저장 및 인증 성공.';
      const summary = response.data.account_summary; // (리스트 받기)
      
      setApiKeyStatus({ message: successMsg, type: 'success' });
      
      if (summary) {
          setAccountSummary(summary); // (리스트 저장)
      }
      
    } catch (error) {
      let errorMsg = 'API 키 인증 실패.';
      if (error.response && error.response.data && error.response.data.detail) {
        errorMsg = error.response.data.detail;
      }
      setApiKeyStatus({ message: errorMsg, type: 'error' });
      setAccountSummary([]); // (실패 시 잔고 숨김)
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
  
  // (모두 선택)
  const handleSelectAll = () => {
    const filteredSymbols = filteredMarkets.map(m => m.market);
    setSelectedMarkets(new Set(filteredSymbols));
  };
  // (모두 해제)
  const handleDeselectAll = () => {
    setSelectedMarkets(new Set());
  };


  // (봇 시작 버튼 클릭)
  const handleStartBots = async () => {
    const botsToStart = Array.from(selectedMarkets).filter(
      (symbol) => !runningBots.has(symbol)
    );
    if (botsToStart.length === 0) {
      addLogMessage('선택된 코인 중 새로 시작할 봇이 없습니다.', 'warn');
      return;
    }
    try {
      addLogMessage(`[${botsToStart.join(', ')}] 봇 시작 요청...`, 'info');
      const response = await axios.post('/api/start', { symbols: botsToStart });
      const started = response.data.started || [];
      setRunningBots(new Set([...runningBots, ...started]));
      if (started.length > 0) {
        addLogMessage(`[${started.join(', ')}] 봇이 성공적으로 시작되었습니다.`, 'success');
      }
    } catch (error) {
      let errorMsg = '봇 시작 실패.';
      if (error.response && error.response.status === 401) {
        errorMsg = "API 키가 설정되지 않았습니다. 0단계에서 API 키를 먼저 저장하세요.";
      } else if (error.response && error.response.data && error.response.data.detail) {
        errorMsg = error.response.data.detail;
      }
      addLogMessage(errorMsg, 'error');
    }
  };

  // (봇 중지 버튼 클릭)
  const handleStopBots = async () => {
     const botsToStop = Array.from(selectedMarkets).filter(
      (symbol) => runningBots.has(symbol)
    );
    if (botsToStop.length === 0) {
      addLogMessage('선택된 코인 중 중지할 봇이 없습니다.', 'warn');
      return;
    }
    try {
      addLogMessage(`[${botsToStop.join(', ')}] 봇 중지 요청...`, 'info');
      const response = await axios.post('/api/stop', { symbols: botsToStop });
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

  // (차트 추가 '+' 버튼 클릭)
  const handleAddChart = () => {
    const newChart = {
      id: Date.now(),
      symbol: 'KRW-ETH',
      interval: 'minute60'
    };
    setCharts(prevCharts => [...prevCharts, newChart]);
  };

  // (차트 삭제 'X' 버튼 클릭)
  const handleRemoveChart = (idToRemove) => {
    if (idToRemove === 1) return; 
    setCharts(prevCharts => prevCharts.filter(chart => chart.id !== idToRemove));
    setChartsData(prevData => {
      const newData = { ...prevData };
      delete newData[idToRemove];
      return newData;
    });
  };

  // (특정 차트의 설정 변경: 코인/인터벌)
  const handleUpdateChart = (idToUpdate, newSettings) => {
    setCharts(prevCharts => 
      prevCharts.map(chart => 
        chart.id === idToUpdate ? newSettings : chart
      )
    );
  };
  
  // --- 렌더링 ---
  
  const filteredMarkets = allMarkets.filter(
    (market) =>
      market.korean_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      market.market.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // [수정] (총 자산 계산)
  // (실시간 Ticker 가격으로 자산 가치 재계산)
  const { totalAssetsKrw, processedAccountSummary } = useMemo(() => {
    let total = 0;
    
    // (accountSummary(매수평균가 기준) -> processedAccountSummary(현재가 기준))
    const processed = accountSummary.map(asset => {
      let value_krw = asset.value_krw; // (기본값: API 인증 시 계산된 값)
      
      if (asset.currency === 'KRW') {
        value_krw = asset.balance;
      } else {
        // (실시간 틱 가격(tickerPrices)이 있으면, 갱신)
        const currentPrice = tickerPrices[`KRW-${asset.currency}`];
        if (currentPrice) {
          value_krw = asset.balance * currentPrice;
        }
      }
      
      total += value_krw;
      return { ...asset, value_krw: value_krw }; // (갱신된 value_krw)
    });

    return { totalAssetsKrw: total, processedAccountSummary: processed };
  // (tickerPrices(실시간 틱) 또는 accountSummary(최초 인증)가 바뀔 때마다 재계산)
  }, [accountSummary, tickerPrices]);


  return (
    <div className="App">
      <header className="App-header">
        <h1>Athena v1 - 자동매매 프로그램</h1>
      </header>
      
      <main className="main-content">
        
        {/* --- 상단 제어판 --- */}
        <div className="control-panel">
          
          {/* --- 0. API 키 설정 --- */}
          <div className="api-keys-section">
            <h2>0. API 키 설정</h2>
            <p>봇을 실행하기 전에 API 키를 저장해야 합니다.</p>
            <input
              type="text"
              placeholder="Upbit Access Key"
              value={accessKey}
              onChange={(e) => {
                setAccessKey(e.target.value);
                setApiKeyStatus({ message: '', type: 'info' });
                setAccountSummary([]); // [수정]
              }}
              className="api-input"
            />
            <input
              type="password"
              placeholder="Upbit Secret Key"
              value={secretKey}
              onChange={(e) => {
                setSecretKey(e.target.value);
                setApiKeyStatus({ message: '', type: 'info' });
                setAccountSummary([]); // [수정]
              }}
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
            
            {/* [수정] (자산 요약 테이블) */}
            {(processedAccountSummary.length > 0 && apiKeyStatus.type === 'success') && (
              <div className="asset-summary-container">
                <table className="asset-table">
                  <thead>
                    <tr>
                      <th>자산</th>
                      <th>보유수량</th>
                      <th>평가(KRW)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {processedAccountSummary.map(asset => (
                      <tr key={asset.currency}>
                        <td>{asset.name} ({asset.currency})</td>
                        <td>
                          {new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 8 }).format(asset.balance)}
                        </td>
                        <td>
                          {new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 0 }).format(asset.value_krw)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="total-assets-row">
                      <td colSpan="2">총 보유자산</td>
                      <td>
                        {new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 0 }).format(totalAssetsKrw)} 원
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
            
          </div>
          
          {/* --- 1. 코인 선택 --- */}
          <div className="market-selector">
            <div 
              className="collapsible-header" 
              onClick={() => setIsCoinListOpen(!isCoinListOpen)}
            >
              <h2>1. 거래 코인 선택</h2>
              <span className="toggle-icon">{isCoinListOpen ? '▲ 숨기기' : '▼ 펼치기'}</span>
            </div>
            
            {isCoinListOpen && (
              <div className="market-list-content">
                <input
                  type="text"
                  placeholder="코인 이름 또는 심볼 검색..."
                  className="search-bar"
                  value={searchQuery}
                  onChange={handleSearchChange}
                />
                
                <div className="market-selection-controls">
                  <div className="button-group-small">
                    <button onClick={handleSelectAll}>필터 모두 선택</button>
                    <button onClick={handleDeselectAll}>모두 해제</button>
                  </div>
                  <div className="market-selection-summary">
                    {selectedMarkets.size} / {allMarkets.length}개 선택됨
                  </div>
                </div>
                
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
        
        {/* --- 하단 컨텐츠 (차트+로그) --- */}
        <div className="main-content-right">
          
          {charts.map((chart, index) => (
            <ChartItem
              key={chart.id}
              chart={chart}
              allMarkets={allMarkets}
              chartData={chartsData[chart.id]} 
              chartTheme={chartTheme}
              realtimeTick={realtimeTick}
              onUpdate={handleUpdateChart}
              onRemove={handleRemoveChart}
              isFixed={index === 0} 
            />
          ))}

          <button className="chart-add-button" onClick={handleAddChart}>
            + 차트 추가
          </button>
          
          <div className={`log-viewer ${isLogOpen ? 'open' : 'closed'}`}>
            <div 
              className="collapsible-header log-header" 
              onClick={() => setIsLogOpen(!isLogOpen)}
            >
              <h2>3. 실시간 로그</h2>
              <span className="toggle-icon">{isLogOpen ? '▲ 숨기기' : '▼ 펼치기'}</span>
            </div>
            
            {isLogOpen && (
              <div className="log-output">
                {logs.map((log, index) => (
                  <div key={index} className={`log-entry ${log.level}`}>
                    <span className="log-timestamp">
                      [{new Date(log.timestamp).toLocaleTimeString()}]
                    </span>
                    <span className="log-message">{log.message}</span>
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            )}
          </div> 
        
        </div> 

      </main>
    </div>
  );
}

export default App;