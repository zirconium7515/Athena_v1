# Athena_v1/ai_trader/strategy/constants.py
# [신규] 2024.11.15 - (Owl v1) pandas-ta 버그 수정을 위한 공용 설정 파일
# [수정] 2024.11.15 - (오류) 'BBL_20_2.0_2.0' 버그 (ta 라이브러리 반환값에 강제 일치)
"""
Strategy Owl v1 - 기술적 분석(TA) 공용 설정

regime.py, patterns.py 등 여러 파일에서 동일한 지표 컬럼 이름을 참조하기 위해
모든 TA 주기를 이 파일에서 중앙 관리합니다.
"""

# === RSI ===
RSI_PERIOD = 14
RSI_COL = f'RSI_{RSI_PERIOD}'

# === 볼린저 밴드 (Bollinger Bands) ===
BBANDS_PERIOD = 20
BBANDS_STD = 2 # (라이브러리가 int 2를 2.0_2.0으로 반환하는 버그 대응)

# [오류 수정] (pandas-ta 라이브러리 버그로 인해, '2.0_2.0'을 강제로 사용)
BBANDS_STD_STR_BUG = "2.0_2.0" 

BBANDS_LOW_COL = f'BBL_{BBANDS_PERIOD}_{BBANDS_STD_STR_BUG}'
BBANDS_MID_COL = f'BBM_{BBANDS_PERIOD}_{BBANDS_STD_STR_BUG}'
BBANDS_UPPER_COL = f'BBU_{BBANDS_PERIOD}_{BBANDS_STD_STR_BUG}'
BBANDS_BANDWIDTH_COL = f'BBB_{BBANDS_PERIOD}_{BBANDS_STD_STR_BUG}'
BBANDS_PERCENT_COL = f'BBP_{BBANDS_PERIOD}_{BBANDS_STD_STR_BUG}'

# (디버깅용)
EXPECTED_BBANDS_COLS = [
    BBANDS_LOW_COL, 
    BBANDS_MID_COL, 
    BBANDS_UPPER_COL, 
    BBANDS_BANDWIDTH_COL, 
    BBANDS_PERCENT_COL
]