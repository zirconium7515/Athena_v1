// Athena_v1/frontend/src/ChartComponent.js
// [수정] 2024.11.11 - (KST 완전 적용)
// [수정] 2024.11.11 - (요청) 차트 양 끝 공백 제거 (fitContent)
// [수정] 2024.11.11 - (오류) addCandlestickSeries 오타 수정
// [수정] 2024.11.11 - (요청) 차트 실시간 갱신 (WebSocket Ticker) 추가
// [수정] 2024.11.11 - (요청) 차트 2단계: 틱(Tick) 라우팅 로직 추가 (props.symbol)
// [수정] 2024.11.11 - (오류) TypeError: ResizeObserver parameter 1 is not of type 'Function' 수정
// [수정] 2024.11.11 - (오류) addCandlistickSeries -> addCandlestickSeries 오타 수정 (재확인)

import React, { useEffect, useRef, useMemo } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

// --- KST 변환 헬퍼 함수 ---

// (십자선용 포맷터: "YYYY-MM-DD HH:MM" (KST))
function formatKST_DateTime(utcTimestamp) {
  const date = new Date(utcTimestamp * 1000);
  const kstOffset = 9 * 60 * 60 * 1000;
  const kstDate = new Date(date.getTime() + kstOffset);
  return kstDate.toISOString().replace('T', ' ').substring(0, 16);
}

// (하단 시간축용 포맷터: "HH:MM" (KST))
function formatKST_Time(utcTimestamp) {
  const date = new Date(utcTimestamp * 1000);
  const kstOffset = 9 * 60 * 60 * 1000;
  const kstDate = new Date(date.getTime() + kstOffset);
  const hours = kstDate.getUTCHours();
  const minutes = kstDate.getUTCMinutes();
  const formattedHours = String(hours).padStart(2, '0');
  const formattedMinutes = String(minutes).padStart(2, '0');
  return `${formattedHours}:${formattedMinutes}`;
}

// --- Ticker 타임스탬프 보정 (Flooring) 헬퍼 ---
function getFlooredTimestamp(timestampMs, intervalStr) {
    const date = new Date(timestampMs);
    
    date.setUTCMilliseconds(0);
    date.setUTCSeconds(0);

    switch (intervalStr) {
        case 'minute1':
            break;
        case 'minute30':
            date.setUTCMinutes(Math.floor(date.getUTCMinutes() / 30) * 30);
            break;
        case 'minute60':
            date.setUTCMinutes(0);
            break;
        case 'minute240':
            date.setUTCMinutes(0);
            date.setUTCHours(Math.floor(date.getUTCHours() / 4) * 4);
            break;
        case 'day':
            date.setUTCMinutes(0);
            date.setUTCHours(0);
            break;
        default:
            break;
    }
    
    return Math.floor(date.getTime() / 1000);
}


// (props: data(캔들), theme(테마 설정), realtimeTick(실시간 틱), chartInterval(시간 단위), symbol(코인))
const ChartComponent = ({ data, theme, realtimeTick, chartInterval, symbol }) => {
  const chartContainerRef = useRef(null); 
  const chartRef = useRef(null); 
  const candleSeriesRef = useRef(null); 

  // (테마 설정)
  const chartOptions = useMemo(() => ({
    layout: {
      background: { type: ColorType.Solid, color: theme.backgroundColor },
      textColor: theme.textColor,
    },
    grid: {
      vertLines: { color: theme.gridColor },
      horzLines: { color: theme.gridColor },
    },
    localization: {
        locale: 'ko-KR',
        timeFormatter: (utcTimestamp) => formatKST_DateTime(utcTimestamp),
    },
    timeScale: {
      timeVisible: true,
      secondsVisible: false,
      tickMarkFormatter: (utcTimestamp) => formatKST_Time(utcTimestamp),
    },
  }), [theme]); 

  // (캔들 시리즈 테마 설정)
  const candleSeriesOptions = useMemo(() => ({
    upColor: theme.upColor,
    downColor: theme.downColor,
    borderUpColor: theme.upColor,
    borderDownColor: theme.downColor,
    wickUpColor: theme.upColor,
    wickDownColor: theme.downColor,
  }), [theme]); 

  // 1. 차트 생성 (컴포넌트 마운트 시 1회)
  useEffect(() => {
    const chart = createChart(chartContainerRef.current, {
      ...chartOptions,
      width: chartContainerRef.current.clientWidth,
      height: 300, 
    });
    chartRef.current = chart;

    // [오타 수정] addCandlistickSeries -> addCandlestickSeries
    const candleSeries = chart.addCandlestickSeries(candleSeriesOptions);
    candleSeriesRef.current = candleSeries;

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candleSeriesOptions]); 

  // 2. 테마 변경 (theme이 바뀔 때)
  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.applyOptions(chartOptions);
    }
    if (candleSeriesRef.current) {
      candleSeriesRef.current.applyOptions(candleSeriesOptions);
    }
  }, [theme, chartOptions, candleSeriesOptions]);

  // 3. (전체) 데이터 변경 (data가 바뀔 때 - 1분 주기 Polling)
  useEffect(() => {
    if (candleSeriesRef.current && data && data.length > 0) {
      candleSeriesRef.current.setData(data);
      chartRef.current.timeScale().fitContent();
    } else if (candleSeriesRef.current) {
      candleSeriesRef.current.setData([]);
    }
  }, [data]); 

  // 4. (수정) 실시간 틱(Tick) 변경 (틱 라우팅)
  useEffect(() => {
    if (!realtimeTick || !candleSeriesRef.current || !chartInterval) {
      return;
    }
    
    if (realtimeTick.code !== symbol) {
      return; 
    }

    try {
      const flooredTimestamp = getFlooredTimestamp(
        realtimeTick.trade_timestamp, 
        chartInterval
      );

      candleSeriesRef.current.update({
        time: flooredTimestamp,
        close: realtimeTick.trade_price 
      });

    } catch (e) {
      console.error("실시간 틱 업데이트 실패:", e);
    }

  }, [realtimeTick, chartInterval, symbol]); 


  // 5. 차트 리사이즈 (컨테이너 크기가 바뀔 때)
  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.resize(
          chartContainerRef.current.clientWidth,
          chartContainerRef.current.clientHeight
        );
      }
    };

    // [오류 수정] (ResizeObserver의 인자로 DOM 요소가 아닌, handleResize 함수를 전달)
    const resizeObserver = new ResizeObserver(handleResize);
    
    // (DOM 요소(ref.current)가 마운트되었는지 확인 후 observe)
    if (chartContainerRef.current) {
        resizeObserver.observe(chartContainerRef.current);
    }

    // (정리)
    return () => {
      resizeObserver.disconnect();
    };
  }, []); // (의존성 배열 비우기)

  return <div ref={chartContainerRef} className="chart-container-inner" />;
};

export default ChartComponent;