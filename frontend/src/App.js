// Athena_v1/frontend/src/App.js
// [수정] 2024.11.11 - (요청) 차트 1단계 및 로그 토글 기능 추가
// [수정] 2024.11.11 - (요청) 새 레이아웃 적용
// [수정] 2024.11.11 - (요청) 차트 자동 갱신 (1분 Polling) 기능 추가
// [수정] 2024.11.11 - (요청) 차트 실시간 갱신 (WebSocket Ticker) 추가
// [수정] 2024.11.11 - (요청) 차트 2단계: 다중 차트 추가/삭제 (+/-)
// [수정] 2024.11.11 - (요청) 1. '모두 선택/해제' 버튼 및 '선택 개수' 추가
// [수정] 2024.11.11 - (요청) API 키 섹션에 '전체 자산 요약(List)' 표시
// [수정] 2024.11.11 - (오류) 'useMemo' is not defined (no-undef) 임포트 누락 수정
// [수정] 2024.11.12 - (요청) 모의 투자 (Simulation) 토글 스위치 추가
// [수정] 2024.11.12 - (요청) 자산 요약(수량) 수동(🔄) 및 자동(10초) 갱신 추가
// [수정] 2024.11.12 - (요청) 자산 요약 테이블에 '수익률(%)' (ROI) 추가
// [수정] 2024.11.12 - (요청) 자산 요약 테이블에 '총 손익 / 총 수익률' 추가

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'; 
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

  const handleSymbolChange = (e) => {
    onUpdate(chart.id, { ...chart, symbol: e.target.value });
  };
  const handleIntervalChange = (interval) => {
    onUpdate(chart.id, { ...chart, interval: interval });
  };

  return (
    <div className="chart-area">
      
      <div className="chart-controls">
        <div className="chart-symbol-select">
          <label>차트 코인:</label>
          <select 
            value={chart.symbol} 
            onChange={handleSymbolChange}
          >
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
        {!isFixed && (
          <button 
            className="chart-remove-button" 
            onClick={() => onRemove(chart.id)}
          >
            ✕
          </button>
        )}
      </div>
      
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
  
  // 0. API 키 및 모드
  const [accessKey, setAccessKey] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [apiKeyStatus, setApiKeyStatus] = useState({ message: '', type: 'info' });
  const [accountSummary, setAccountSummary] = useState([]); 
  const [isMockTrade, setIsMockTrade] = useState(false); 

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
  const [tickerPrices, setTickerPrices] = useState({}); 
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
          setRealtimeTick(msg.payload);
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


  // --- 차트 실시간 구독 (보유 자산 포함) ---
  useEffect(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      
      const chartSymbols = charts.map(c => c.symbol);
      const heldSymbols = accountSummary
        .filter(asset => asset.currency !== 'KRW')
        .map(asset => `KRW-${asset.currency}`);
        
      const symbolsToSubscribe = Array.from(new Set([...chartSymbols, ...heldSymbols]));
      
      if (symbolsToSubscribe.length > 0) {
        wsRef.current.send(JSON.stringify({
          type: "subscribe_charts_list",
          symbols: symbolsToSubscribe
        }));
      }
      
      setRealtimeTick(null);
    }
  }, [charts, accountSummary]); 

  // --- 자산 요약(수량) 자동 갱신 (10초) ---
  useEffect(() => {
    if (apiKeyStatus.type !== 'success') {
      return; 
    }
    
    const intervalId = setInterval(() => {
        handleRefreshAssets();
    }, 10000); // 10초

    return () => clearInterval(intervalId); 
  
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKeyStatus.type]); 


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
  
  // (API 키/모드 저장)
  const handleSetApiKeys = async () => {
    if (!isMockTrade && (!accessKey || !secretKey)) {
      setApiKeyStatus({ message: '실전 매매 모드에서는 Access Key와 Secret Key를 모두 입력해야 합니다.', type: 'error' });
      return;
    }
    
    setApiKeyStatus({ message: isMockTrade ? '모의 투자 모드 시작 중...' : 'API 키 인증 중...', type: 'info' });
    setAccountSummary([]); 
    
    try {
      const payload = {
        is_mock_trade: isMockTrade,
        access_key: accessKey,
        secret_key: secretKey
      };
      
      const response = await axios.post('/api/set-keys', payload);
      
      const successMsg = response.data.message || '설정 완료.';
      const summary = response.data.account_summary; 
      
      setApiKeyStatus({ message: successMsg, type: 'success' });
      
      if (summary) {
          setAccountSummary(summary); 
      }
      
    } catch (error) {
      let errorMsg = '설정 실패.';
      if (error.response && error.response.data && error.response.data.detail) {
        errorMsg = error.response.data.detail;
      }
      setApiKeyStatus({ message: errorMsg, type: 'error' });
      setAccountSummary([]); 
    }
  };
  
  // (자산 요약(수량) 수동 갱신)
  const handleRefreshAssets = async () => {
    if (apiKeyStatus.type !== 'success') {
      return;
    }
    
    try {
      const response = await axios.get('/api/account-summary');
      const summary = response.data.account_summary;
      if (summary) {
          setAccountSummary(summary);
      }
    } catch (error) {
      console.error("자산 요약 갱신 실패:", error);
      addLogMessage("자산 요약(수량) 갱신에 실패했습니다. (백엔드 /api/account-summary 오류)", "error");
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
        errorMsg = "API 키 또는 모의 투자 모드가 설정되지 않았습니다. 0단계에서 먼저 설정을 완료하세요.";
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

  // [수정] (요청) (총 자산, 총 손익, 총 수익률 계산)
  const { totalAssetsKrw, processedAccountSummary, totalProfitLoss, totalRoi } = useMemo(() => {
    let totalValue = 0; // (총 평가 금액)
    let totalCost = 0; // (총 매수 금액)
    
    const processed = accountSummary.map(asset => {
      let value_krw = asset.value_krw; 
      let cost_basis = 0;
      let roi = 0; 
      
      if (asset.currency === 'KRW') {
        value_krw = asset.balance;
        cost_basis = asset.balance; // (KRW의 매수가는 1)
      } else {
        cost_basis = asset.balance * asset.avg_buy_price; // (매수 금액)
        
        const currentPrice = tickerPrices[`KRW-${asset.currency}`];
        if (currentPrice) {
          value_krw = asset.balance * currentPrice; // (현재 평가액)
          
          if (asset.avg_buy_price > 0) {
              roi = ((currentPrice - asset.avg_buy_price) / asset.avg_buy_price) * 100;
          }
        }
        // (틱 가격이 없으면, 10초 갱신 시의 value_krw를 사용)
      }
      
      totalValue += value_krw;
      totalCost += cost_basis;
      return { ...asset, value_krw: value_krw, roi: roi }; 
    });

    // (총 손익 및 총 수익률 계산)
    const totalPL = totalValue - totalCost;
    const totalROI = (totalCost > 0) ? (totalPL / totalCost) * 100 : 0;

    return { 
      totalAssetsKrw: totalValue, 
      processedAccountSummary: processed,
      totalProfitLoss: totalPL,
      totalRoi: totalROI
    };
  }, [accountSummary, tickerPrices]);


  return (
    <div className="App">
      <header className="App-header">
        <h1>Athena v1 - 자동매매 프로그램</h1>
      </header>
      
      <main className="main-content">
        
        {/* --- 상단 제어판 --- */}
        <div className="control-panel">
          
          {/* --- 0. API 키 / 모드 설정 --- */}
          <div className="api-keys-section">
            
            <div className="collapsible-header api-header">
              <h2>0. 실행 모드 설정</h2>
              {apiKeyStatus.type === 'success' && (
                <button 
                  className="asset-refresh-button" 
                  onClick={handleRefreshAssets}
                  title="자산 수량(모의/실전)을 지금 갱신합니다."
                >
                  🔄 갱신
                </button>
              )}
            </div>
            
            <div className="mode-toggle-switch">
              <span className={!isMockTrade ? 'active' : ''}>실전 매매</span>
              <label className="switch">
                <input 
                  type="checkbox" 
                  checked={isMockTrade} 
                  onChange={(e) => {
                    setIsMockTrade(e.target.checked);
                    setApiKeyStatus({ message: '', type: 'info' });
                    setAccountSummary([]);
                  }} 
                />
                <span className="slider round"></span>
              </label>
              <span className={isMockTrade ? 'active' : ''}>모의 투자</span>
            </div>
            
            <input
              type="text"
              placeholder="Upbit Access Key"
              value={accessKey}
              disabled={isMockTrade} 
              onChange={(e) => {
                setAccessKey(e.target.value);
                setApiKeyStatus({ message: '', type: 'info' });
                setAccountSummary([]); 
              }}
              className="api-input"
            />
            <input
              type="password"
              placeholder="Upbit Secret Key"
              value={secretKey}
              disabled={isMockTrade} 
              onChange={(e) => {
                setSecretKey(e.target.value);
                setApiKeyStatus({ message: '', type: 'info' });
                setAccountSummary([]); 
              }}
              className="api-input"
            />
            
            <button 
              onClick={handleSetApiKeys} 
              className={`api-button ${isMockTrade ? 'mock' : 'real'}`}
            >
              {isMockTrade ? '모의 투자 시작 (가상 1000만원)' : '실전 API 키 저장'}
            </button>
            
            {apiKeyStatus.message && (
              <div className={`api-status ${apiKeyStatus.type}`}>
                {apiKeyStatus.message}
              </div>
            )}
            
            {/* [수정] (요청) (자산 요약 테이블) */}
            {(processedAccountSummary.length > 0 && apiKeyStatus.type === 'success') && (
              <div className="asset-summary-container">
                <table className="asset-table">
                  <thead>
                    <tr>
                      <th>자산</th>
                      <th>보유수량</th>
                      <th>평가(KRW)</th>
                      <th>수익률 (%)</th> 
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
                        <td className={
                          asset.roi > 0 ? 'roi-positive' : (asset.roi < 0 ? 'roi-negative' : 'roi-neutral')
                        }>
                          {asset.currency !== 'KRW' ? `${asset.roi.toFixed(2)} %` : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  {/* [수정] (요청) (총 손익/수익률 행 추가) */}
                  <tfoot>
                    <tr className="total-assets-row">
                      {/* [수정] (colSpan 3 -> 2) */}
                      <td colSpan="2">총 보유자산</td>
                      <td>
                        {new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 0 }).format(totalAssetsKrw)} 원
                      </td>
                      <td></td> {/* (수익률 빈 칸) */}
                    </tr>
                    {/* [신규] (총 손익/수익률) */}
                    <tr className="total-roi-row">
                      <td colSpan="2">총 손익 (P/L)</td>
                      <td className={
                        totalProfitLoss > 0 ? 'roi-positive' : (totalProfitLoss < 0 ? 'roi-negative' : 'roi-neutral')
                      }>
                        {new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 0 }).format(totalProfitLoss)} 원
                      </td>
                      <td className={
                        totalRoi > 0 ? 'roi-positive' : (totalRoi < 0 ? 'roi-negative' : 'roi-neutral')
                      }>
                        {totalRoi.toFixed(2)} %
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