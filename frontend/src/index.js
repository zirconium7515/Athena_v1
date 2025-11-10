// Athena_v1/frontend/src/index.js
// [수정] 2024.11.11 - reportWebVitals 관련 404 오류 해결을 위해 주석 처리

import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
// import reportWebVitals from './reportWebVitals'; // (404 오류로 주석 처리)

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
// reportWebVitals(); // (404 오류로 주석 처리)