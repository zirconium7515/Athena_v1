Athena v1 - 설치 및 실행 가이드이 문서는 Athena v1 자동매매 프로그램을 설치하고 실행하는 방법을 안내합니다.프로그램은 '백엔드'(매매 로직)와 '프론트엔드'(GUI) 두 부분으로 나뉘어 실행됩니다.1. 최소 요구 사항Python: 3.10 이상Node.js: 18.x 이상 (React GUI 실행용)Git: (GitHub 백업 및 다운로드 시 필요)Upbit API 키: (실제 거래를 위해 .env 파일에 필요)2. 설치 및 설정 (최초 1회)(권장) 1단계: Python 가상환경 구축프로젝트 폴더(Athena_v1)를 새로 만들고, 해당 폴더 내에 Python 가상환경을 설정하여 라이브러리 충돌을 방지합니다.프로젝트 폴더(Athena_v1)로 이동합니다.터미널에 다음 명령어를 입력하여 venv라는 이름의 가상환경을 생성합니다.python -m venv venv
생성된 가상환경을 활성화합니다.(Windows - CMD/PowerShell):.\venv\Scripts\activate
(macOS/Linux - Bash):source venv/bin/activate
(터미널 프롬프트 앞에 (venv)가 표시되면 성공입니다. 이후 모든 백엔드 명령어는 이 터미널에서 실행합니다.)2단계: 백엔드 (Python) 의존성 설치Athena_v1 루트 폴더에서 requirements.txt 파일에 정의된 라이브러리들을 설치합니다.# (위치: Athena_v1)
# (venv)가 활성화된 상태여야 합니다.
pip install -r requirements.txt
3단계: API 키 설정Athena_v1 루트 폴더에 .env 파일을 생성하고, 발급받은 업비트 API 키를 입력합니다. (제공된 .env 파일의 YOUR_..._HERE 부분을 수정합니다.)# Athena_v1/.env 파일 내용 예시
UPBIT_ACCESS_KEY=YOUR_ACCESS_KEY_HERE
UPBIT_SECRET_KEY=YOUR_SECRET_KEY_HERE
(주의) 이 파일은 .gitignore에 의해 GitHub에 백업되지 않으므로, 별도로 안전하게 보관해야 합니다.4단계: 프론트엔드 (React) 의존성 설치frontend 폴더로 이동하여 React 실행에 필요한 라이브러리(axios 등)를 설치합니다.# (위치: Athena_v1)
cd frontend

# (위치: Athena_v1/frontend)
npm install
3. 프로그램 실행프로그램을 실행하려면 2개의 터미널이 필요합니다.1단계: (터미널 1) 백엔드 서버 시작Athena_v1 루트 폴더에서 (가상환경이 활성화된 상태로) uvicorn 명령어를 사용해 FastAPI 백엔드 서버를 시작합니다.# (위치: Athena_v1)
# (venv)가 활성화된 상태여야 합니다.
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
--reload 옵션은 코드가 변경될 때마다 서버를 자동으로 재시작해 줍니다.INFO: Uvicorn running on http://127.0.0.1:8000 메시지가 나오면 성공입니다.2단계: (터미널 2) 프론트엔드 GUI 시작Athena_v1/frontend 폴더에서 npm start 명령어를 사용해 React 개발 서버를 시작합니다.# (위치: Athena_v1/frontend)
npm start
이 명령어를 실행하면 자동으로 웹 브라우저가 열리고 http://localhost:3000 주소로 GUI가 표시됩니다.3단계: GUI 접속웹 브라우저에서 http://localhost:3000 주소로 접속하여 GUI를 사용합니다.4. GUI 사용법코인 선택:왼쪽 '1. 거래 코인 선택' 목록에서 거래하려는 코인(예: KRW-BTC)을 클릭하여 선택합니다.검색창을 이용해 원하는 코인을 쉽게 찾을 수 있습니다.'전체 선택' / '전체 해제' 버튼을 사용할 수 있습니다.봇 시작:원하는 코인들을 모두 선택한 상태에서, 가운데 '2. 봇 제어' 섹션의 [선택 봇 시작] 버튼을 클릭합니다.'3. 실행중인 봇' 목록에 해당 코인들이 표시되고, '실행중' 배지가 붙습니다.오른쪽 '4. 실시간 로그'에 봇이 시작되었다는 메시지가 표시됩니다.봇 중지:중지하려는 봇(실행 중인 코인)을 다시 클릭하여 선택합니다.[선택 봇 중지] 버튼을 클릭합니다.'실행중인 봇' 목록에서 해당 코인이 사라지고 로그가 출력됩니다.로그 확인:모든 봇의 활동(신호 감지, 진입, 청산, 오류 등)은 '4. 실시간 로그' 창에 실시간으로 표시됩니다.