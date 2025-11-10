Athena v1 - 자동매매 프로그램 사용 가이드
이 문서는 'Athena v1' 프로그램을 로컬 컴퓨터에서 설치하고 실행하는 방법과GUI(사용자 인터페이스)를 통해 봇을 작동하는 방법을 설명합니다.

1. 사전 준비 사항프로그램을 실행하기 위해 다음 소프트웨어가 설치되어 있어야 합니다. Python: 버전 3.10 이상 (https://www.python.org/downloads/) 
Node.js & npm: 버전 18.x 이상 (https://nodejs.org/ko) (프론트엔드 GUI 실행용)
업비트 API 키:Access Key와 Secret Key가 필요합니다.(중요) API 발급 시, '자산 조회', '주문 조회', '주문하기' 권한이 필요하며, 반드시 특정 IP에서만 실행하도록 IP를 등록해야 합니다.

2. 설치 및 설정프로그램 실행 전, 딱 한 번만 수행하면 되는 초기 설정 단계입니다.(권장) 1단계: Python 가상환경 구축왜 필요한가요?가상환경은 'Athena v1'만을 위한 '독립된 방'을 만들어주는 것과 같습니다. 이 프로그램에 필요한 라이브러리들(fastapi, pandas 등)이 PC의 다른 프로그램과 섞이지 않게 격리하여, 라이브러리 버전 충돌로 인한 오류를 방지합니다. 안정적인 24시간 구동을 위해 강력히 권장됩니다.Athena_v1 폴더로 이동한 터미널에서 다음 명령어를 실행합니다.(폴더 내에 venv라는 이름의 가상환경이 생성됩니다.)
```
python -m venv venv
```
가상환경을 활성화합니다. (터미널을 켤 때마다 실행 필요)
```
Windows (CMD):.\venv\Scripts\activate
macOS/Linux (Bash):source venv/bin/activate
```
활성화되면 터미널 프롬프트 앞에 (venv)가 표시됩니다.

2단계: API 키 입력Athena_v1 폴더 안에 있는 .env 파일을 엽니다.파일 내의 YOUR_ACCESS_KEY_HERE와 YOUR_SECRET_KEY_HERE 부분을 실제 발급받은 업비트 API 키로 교체하고 저장합니다.# Athena_v1/.env

UPBIT_ACCESS_KEY=실제 Access Key를 여기에 붙여넣기
UPBIT_SECRET_KEY=실제 Secret Key를 여기에 붙여넣기...

3단계: 백엔드 (Python) 의존성 설치터미널(명령 프롬프트)을 엽니다.Athena_v1 프로젝트 폴더로 이동합니다.(중요) 1단계에서 가상환경을 만들었다면, **반드시 가상환경이 활성화된 상태((venv) 표시 확인)**여야 합니다.cd 경로/Ahtena_v1
다음 명령어를 입력하여 필요한 Python 라이브러리를 모두 설치합니다.pip install -r requirements.txt
4단계: 프론트엔드 (React) 의존성 설치터미널에서 Athena_v1/frontend 폴더로 이동합니다.cd frontend
(이미 Athena_v1 폴더에 있다면 cd frontend만 입력)2.  다음 명령어를 입력하여 GUI에 필요한 라이브러리를 모두 설치합니다. (시간이 다소 걸릴 수 있습니다.)npm install

3. 프로그램 실행 (중요)
백엔드(서버)와 프론트엔드(GUI)는 반드시 2개의 터미널에서 각각 따로 실행해야 합니다.

터미널 1: 백엔드 (서버) 실행새 터미널을 엽니다.Athena_v1 루트 폴더로 이동합니다.cd 경로/Athena_v1
(중요) 가상환경을 만들었다면, 먼저 활성화합니다..
```
\venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```
다음 명령어를 입력하여 백엔드 서버를 시작합니다.
```
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
또는python main.py
```
터미널에 Application startup complete. 같은 메시지가 보이고 (http://127.0.0.1:8000)에서 서버가 실행 중이라는 로그가 뜨면 성공입니다. 이 터미널은 끄지 말고 그대로 두어야 합니다.

터미널 2: 프론트엔드 (GUI) 실행새로운 터미널을 엽니다. (기존 백엔드 터미널은 그대로 둡니다)Athena_v1/frontend 폴더로 이동합니다.
```cd 경로/Athena_v1/frontend```
다음 명령어를 입력하여 GUI를 시작합니다.
```npm start```
자동으로 웹 브라우저가 열리며 http://localhost:3000 주소로 접속됩니다. (만약 열리지 않으면 주소창에 직접 입력)

4. GUI 사용 방법
http://localhost:3000에 접속하면 Athena v1 대시보드가 나타납니다.(확인) 헤더 우측 상단에 서버 연결됨이라는 녹색 불이 들어오는지 확인합니다. (만약 빨간 불이면 백엔드 실행(3-1)이 정상인지 확인)(선택) 
1. 거래 코인 선택 (왼쪽)거래를 원하는 코인을 검색하거나 스크롤하여 찾습니다.코인(예: KRW-BTC)을 클릭하면 파란색으로 '선택'됩니다. (다중 선택 가능)전체 선택 / 전체 해제 버튼을 사용할 수 있습니다.(시작) 
2. 봇 제어 (가운데)코인을 선택한 상태에서 선택 봇 시작 버튼을 누릅니다.
4. 실시간 로그 (오른쪽)에 [KRW-BTC] 트레이딩 봇 시작. 로그가 나타납니다.
3. 실행중인 봇 목록Athena v1 - 자동매매 프로그램 사용 가이드이 문서는 'Athena v1' 프로그램을 로컬 컴퓨터에서 설치하고 실행하는 방법과GUI(사용자 인터페이스)를 통해 봇을 작동하는 방법을 설명합니다.1. 사전 준비 사항프로그램을 실행하기 위해 다음 소프트웨어가 설치되어 있어야 합니다.Python: 버전 3.10 이상 (https://www.python.org/downloads/)Node.js & npm: 버전 18.x 이상 (https://nodejs.org/ko) (프론트엔드 GUI 실행용)업비트 API 키:Access Key와 Secret Key가 필요합니다.(중요) API 발급 시, '자산 조회', '주문 조회', '주문하기' 권한이 필요하며, 반드시 특정 IP에서만 실행하도록 IP를 등록해야 합니다.2. 설치 및 설정프로그램 실행 전, 딱 한 번만 수행하면 되는 초기 설정 단계입니다.(권장) 1단계: Python 가상환경 구축왜 필요한가요?가상환경은 'Athena v1'만을 위한 '독립된 방'을 만들어주는 것과 같습니다. 이 프로그램에 필요한 라이브러리들(fastapi, pandas 등)이 PC의 다른 프로그램과 섞이지 않게 격리하여, 라이브러리 버전 충돌로 인한 오류를 방지합니다. 안정적인 24시간 구동을 위해 강력히 권장됩니다.Athena_v1 폴더로 이동한 터미널에서 다음 명령어를 실행합니다.(폴더 내에 venv라는 이름의 가상환경이 생성됩니다.)python -m venv venv
가상환경을 활성화합니다. (터미널을 켤 때마다 실행 필요)Windows (CMD):.\venv\Scripts\activate
macOS/Linux (Bash):source venv/bin/activate
활성화되면 터미널 프롬프트 앞에 (venv)가 표시됩니다.2단계: API 키 입력Athena_v1 폴더 안에 있는 .env 파일을 엽니다.파일 내의 YOUR_ACCESS_KEY_HERE와 YOUR_SECRET_KEY_HERE 부분을 실제 발급받은 업비트 API 키로 교체하고 저장합니다.# Athena_v1/.env

UPBIT_ACCESS_KEY=실제 Access Key를 여기에 붙여넣기
UPBIT_SECRET_KEY=실제 Secret Key를 여기에 붙여넣기
...
3단계: 백엔드 (Python) 의존성 설치터미널(명령 프롬프트)을 엽니다.Athena_v1 프로젝트 폴더로 이동합니다.(중요) 1단계에서 가상환경을 만들었다면, **반드시 가상환경이 활성화된 상태((venv) 표시 확인)**여야 합니다.cd 경로/Ahtena_v1
다음 명령어를 입력하여 필요한 Python 라이브러리를 모두 설치합니다.pip install -r requirements.txt
4단계: 프론트엔드 (React) 의존성 설치터미널에서 Athena_v1/frontend 폴더로 이동합니다.cd frontend
(이미 Athena_v1 폴더에 있다면 cd frontend만 입력)2.  다음 명령어를 입력하여 GUI에 필요한 라이브러리를 모두 설치합니다. (시간이 다소 걸릴 수 있습니다.)npm install
3. 프로그램 실행 (중요)백엔드(서버)와 프론트엔드(GUI)는 반드시 2개의 터미널에서 각각 따로 실행해야 합니다.터미널 1: 백엔드 (서버) 실행새 터미널을 엽니다.Athena_v1 루트 폴더로 이동합니다.cd 경로/Athena_v1
(중요) 가상환경을 만들었다면, 먼저 활성화합니다..\venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
다음 명령어를 입력하여 백엔드 서버를 시작합니다.uvicorn main:app --host 127.0.0.1 --port 8000 --reload
또는python main.py
터미널에 Application startup complete. 같은 메시지가 보이고 (http://127.0.0.1:8000)에서 서버가 실행 중이라는 로그가 뜨면 성공입니다. 이 터미널은 끄지 말고 그대로 두어야 합니다.터미널 2: 프론트엔드 (GUI) 실행새로운 터미널을 엽니다. (기존 백엔드 터미널은 그대로 둡니다)Athena_v1/frontend 폴더로 이동합니다.cd 경로/Athena_v1/frontend
다음 명령어를 입력하여 GUI를 시작합니다.npm start
자동으로 웹 브라우저가 열리며 http://localhost:3000 주소로 접속됩니다. (만약 열리지 않으면 주소창에 직접 입력)4. GUI 사용 방법http://localhost:3000에 접속하면 Athena v1 대시보드가 나타납니다.(확인) 헤더 우측 상단에 서버 연결됨이라는 녹색 불이 들어오는지 확인합니다. (만약 빨간 불이면 백엔드 실행(3-1)이 정상인지 확인)(선택) 1. 거래 코인 선택 (왼쪽)거래를 원하는 코인을 검색하거나 스크롤하여 찾습니다.코인(예: KRW-BTC)을 클릭하면 파란색으로 '선택'됩니다. (다중 선택 가능)전체 선택 / 전체 해제 버튼을 사용할 수 있습니다.(시작) 2. 봇 제어 (가운데)코인을 선택한 상태에서 선택 봇 시작 버튼을 누릅니다.4. 실시간 로그 (오른쪽)에 [KRW-BTC] 트레이딩 봇 시작. 로그가 나타납니다.3. 실행중인 봇 목록에 해당 코인이 표시되며, 왼쪽 코인 목록에도 실행중 배지가 붙습니다.이제 해당 코인(들)은 10분마다 (main.py의 await asyncio.sleep(600)) Strategy v3.5 신호를 확인하기 시작합니다.(중지)중지하려는 코인(현재 실행중인 코인)을 다시 클릭하여 '선택'합니다.선택 봇 중지 버튼을 누릅니다.봇이 중지되고 목록에서 사라집니다.5. 중요 참고 사항전략 로직: 현재 ai_trader/strategy/ 폴더 내의 피벗, 오더블록, 패턴 인식 로직은 Strategy v3.5 문서를 기반으로 한 **초기 구현체(시뮬레이션)**입니다. 실제 매매에 투입하기 전에 해당 로직들을 면밀히 검토하고 전략 문서와 100% 일치하도록 정교화하는 작업(TODO)이 필요합니다.24시간 구동: 현재 방식(로컬 PC)은 24시간 구동에 적합하지 않습니다. 안정적인 운영을 위해서는 AWS, GCP 같은 클라우드 서버나 개인 서버(NAS 등)에 이 프로그램을 배포해야 합니다.부록: GitHub 백업 및 관리 가이드이 섹션은 Athena_v1 프로젝트를 GitHub에 새로 백업(업로드)하고, 변경 사항을 업데이트하며, 다른 컴퓨터에 다운로드(복제)하는 방법을 설명합니다.0. 사전 준비 사항Git 설치: 이 모든 작업을 수행하려면 컴퓨터에 Git이 설치되어 있어야 합니다. (https://git-scm.com/downloads/)GitHub 계정: GitHub 웹사이트(https://www.google.com/search?q=https://github.com/)%EC%97%90%EC%84%9C 계정을 생성해야 합니다.1. 새 프로젝트 GitHub에 처음 업로드하기 (백업)로컬 컴퓨터에 있는 Athena_v1 폴더 전체를 GitHub에 새로 백업하는 과정입니다.1단계: GitHub에서 새 저장소(Repository) 생성GitHub 웹사이트에 로그인합니다.우측 상단의 + 아이콘을 클릭한 후, New repository를 선택합니다.Repository name에 Athena_v1 (또는 원하시는 다른 이름)을 입력합니다.Public (공개) 또는 Private (비공개)를 선택합니다.(권장) Private를 선택하세요. API 키 등 민감한 정보가 실수로 노출되는 것을 막기 위해 비공개로 설정하는 것이 좋습니다.중요: Add a README file, Add .gitignore, Choose a license 항목은 모두 체크 해제한 상태로 둡니다. (이미 로컬에 파일들이 있기 때문입니다)Create repository 버튼을 클릭합니다.2단계: 터미널에서 로컬 프로젝트 업로드PC에서 터미널(명령 프롬프트)을 엽니다.Athena_v1 루트 폴더로 이동합니다.cd 경로/Athena_v1
다음 명령어들을 순서대로 입력합니다.# 1. 이 폴더를 Git 저장소로 초기화합니다.
git init

# 2. (선택) 기본 브랜치 이름을 'main'으로 설정합니다.
git branch -M main

# 3. GitHub에서 생성한 저장소 주소를 'origin'이라는 이름으로 연결합니다.
# [YOUR_USERNAME]과 [REPOSITORY_NAME]을 실제 정보로 바꿔야 합니다.
# (예: [https://github.com/my-id/Athena_v1.git](https://github.com/my-id/Athena_v1.git))
# (이 주소는 1단계 완료 후 GitHub 페이지에 표시됩니다)
git remote add origin [https://github.com/](https://github.com/)[YOUR_USERNAME]/[REPOSITORY_NAME].git

# 4. .gitignore에 명시된 파일(.env 등)을 제외하고 모든 파일을 추가(stage)합니다.
git add .

# 5. '첫 번째 버전'이라는 메시지와 함께 로컬에 저장(commit)합니다.
git commit -m "Initial commit: Athena v1"

# 6. 로컬에 저장된 내용을 GitHub 서버('origin')로 업로드(push)합니다.
git push -u origin main
(참고) git push 실행 시 GitHub 사용자 이름과 비밀번호(또는 토큰)를 물어볼 수 있습니다.업로드가 완료되면 GitHub 저장소 페이지를 새로고침하여 파일들이 모두 백업되었는지 확인합니다. (.env 파일과 athena_v1.log, athena_v1_trade_history.db 등은 .gitignore에 의해 제외되는 것이 정상입니다.)2. 변경된 코드 업데이트하기 (수정 사항 반영)프로젝트 코드를 수정한 후(예: main.py 파일 수정), 변경된 내용을 GitHub 백업에 덮어쓰는(업데이트) 과정입니다.터미널을 열고 Athena_v1 루트 폴더로 이동합니다.cd 경로/Athena_v1
다음 명령어들을 순서대로 입력합니다.# 1. 수정되거나 추가된 모든 파일들을 Git에 알립니다.
git add .

# 2. 어떤 내용을 수정했는지 메시지를 남기고 로컬에 저장(commit)합니다.
# (메시지는 "버그 수정", "로그인 기능 추가"처럼 구체적으로 적는 것이 좋습니다)
git commit -m "Update: main.py에서 신호 생성 로직 수정"

# 3. 로컬에 저장된 최신 버전을 GitHub 서버로 업로드(push)합니다.
git push origin main
3. 다른 컴퓨터에서 다운로드하기 (원격 복제)GitHub에 백업된 Athena_v1 프로젝트를 다른 PC(예: AWS 클라우드 서버)로 그대로 복제해오는 과정입니다.새 컴퓨터에 Git이 설치되어 있는지 확인합니다.프로젝트를 다운로드할 폴더로 터미널을 열고 이동합니다.GitHub 저장소 페이지에서 Code 버튼(초록색)을 누르고 HTTPS 주소(예: https://github.com/my-id/Athena_v1.git)를 복사합니다.터미널에 다음 명령어를 입력합니다.git clone [복사한_HTTPS_주소]
(예: git clone https://github.com/my-id/Athena_v1.git)Athena_v1 폴더가 통째로 다운로드됩니다.중요: 다운로드 후 실행 준비 (필수)GitHub에서 다운로드한 직후에는 3가지 파일/폴더가 없기 때문에 바로 실행되지 않습니다. (.gitignore 때문에 백업에서 제외되었기 때문입니다.)다운로드한 Athena_v1 폴더에서 다음 작업을 수행해야 합니다..env 파일 생성:Athena_v1 폴더 안에 .env 파일을 새로 만듭니다.백업해 둔 실제 업비트 API 키를 이 파일에 입력하고 저장합니다. (가이드 본문 2-2단계: API 키 입력 참고)백엔드 의존성 설치:터미널에서 Athena_v1 폴더로 이동합니다.(가상환경을 사용한다면 python -m venv venv 및 활성화 먼저 수행)pip install -r requirements.txt 를 실행합니다.프론트엔드 의존성 설치 (node_modules):터미널에서 Athena_v1/frontend 폴더로 이동합니다.npm install 을 실행합니다.이 3가지 작업이 완료되면 가이드 본문의 3. 프로그램 실행 단계에 따라 백엔드와 프론트엔드를 실행할 수 있습니다.에 해당 코인이 표시되며, 왼쪽 코인 목록에도 실행중 배지가 붙습니다.이제 해당 코인(들)은 10분마다 (main.py의 await asyncio.sleep(600)) Strategy v3.5 신호를 확인하기 시작합니다.(중지)중지하려는 코인(현재 실행중인 코인)을 다시 클릭하여 '선택'합니다.선택 봇 중지 버튼을 누릅니다.봇이 중지되고 목록에서 사라집니다.5. 중요 참고 사항전략 로직: 현재 ai_trader/strategy/ 폴더 내의 피벗, 오더블록, 패턴 인식 로직은 Strategy v3.5 문서를 기반으로 한 **초기 구현체(시뮬레이션)**입니다. 실제 매매에 투입하기 전에 해당 로직들을 면밀히 검토하고 전략 문서와 100% 일치하도록 정교화하는 작업(TODO)이 필요합니다.24시간 구동: 현재 방식(로컬 PC)은 24시간 구동에 적합하지 않습니다. 안정적인 운영을 위해서는 AWS, GCP 같은 클라우드 서버나 개인 서버(NAS 등)에 이 프로그램을 배포해야 합니다.부록: GitHub 백업 및 관리 가이드이 섹션은 Athena_v1 프로젝트를 GitHub에 새로 백업(업로드)하고, 변경 사항을 업데이트하며, 다른 컴퓨터에 다운로드(복제)하는 방법을 설명합니다.0. 사전 준비 사항Git 설치: 이 모든 작업을 수행하려면 컴퓨터에 Git이 설치되어 있어야 합니다. (https://git-scm.com/downloads/)GitHub 계정: GitHub 웹사이트(https://www.google.com/search?q=https://github.com/)%EC%97%90%EC%84%9C 계정을 생성해야 합니다.1. 새 프로젝트 GitHub에 처음 업로드하기 (백업)로컬 컴퓨터에 있는 Athena_v1 폴더 전체를 GitHub에 새로 백업하는 과정입니다.1단계: GitHub에서 새 저장소(Repository) 생성GitHub 웹사이트에 로그인합니다.우측 상단의 + 아이콘을 클릭한 후, New repository를 선택합니다.Repository name에 Athena_v1 (또는 원하시는 다른 이름)을 입력합니다.Public (공개) 또는 Private (비공개)를 선택합니다.(권장) Private를 선택하세요. API 키 등 민감한 정보가 실수로 노출되는 것을 막기 위해 비공개로 설정하는 것이 좋습니다.중요: Add a README file, Add .gitignore, Choose a license 항목은 모두 체크 해제한 상태로 둡니다. (이미 로컬에 파일들이 있기 때문입니다)Create repository 버튼을 클릭합니다.2단계: 터미널에서 로컬 프로젝트 업로드PC에서 터미널(명령 프롬프트)을 엽니다.Athena_v1 루트 폴더로 이동합니다.cd 경로/Athena_v1
다음 명령어들을 순서대로 입력합니다.# 1. 이 폴더를 Git 저장소로 초기화합니다.
git init

# 2. (선택) 기본 브랜치 이름을 'main'으로 설정합니다.
git branch -M main

# 3. GitHub에서 생성한 저장소 주소를 'origin'이라는 이름으로 연결합니다.
# [YOUR_USERNAME]과 [REPOSITORY_NAME]을 실제 정보로 바꿔야 합니다.
# (예: [https://github.com/my-id/Athena_v1.git](https://github.com/my-id/Athena_v1.git))
# (이 주소는 1단계 완료 후 GitHub 페이지에 표시됩니다)
git remote add origin [https://github.com/](https://github.com/)[YOUR_USERNAME]/[REPOSITORY_NAME].git

# 4. .gitignore에 명시된 파일(.env 등)을 제외하고 모든 파일을 추가(stage)합니다.
git add .

# 5. '첫 번째 버전'이라는 메시지와 함께 로컬에 저장(commit)합니다.
git commit -m "Initial commit: Athena v1"

# 6. 로컬에 저장된 내용을 GitHub 서버('origin')로 업로드(push)합니다.
git push -u origin main
(참고) git push 실행 시 GitHub 사용자 이름과 비밀번호(또는 토큰)를 물어볼 수 있습니다.업로드가 완료되면 GitHub 저장소 페이지를 새로고침하여 파일들이 모두 백업되었는지 확인합니다. (.env 파일과 athena_v1.log, athena_v1_trade_history.db 등은 .gitignore에 의해 제외되는 것이 정상입니다.)2. 변경된 코드 업데이트하기 (수정 사항 반영)프로젝트 코드를 수정한 후(예: main.py 파일 수정), 변경된 내용을 GitHub 백업에 덮어쓰는(업데이트) 과정입니다.터미널을 열고 Athena_v1 루트 폴더로 이동합니다.cd 경로/Athena_v1
다음 명령어들을 순서대로 입력합니다.# 1. 수정되거나 추가된 모든 파일들을 Git에 알립니다.
git add .

# 2. 어떤 내용을 수정했는지 메시지를 남기고 로컬에 저장(commit)합니다.
# (메시지는 "버그 수정", "로그인 기능 추가"처럼 구체적으로 적는 것이 좋습니다)
git commit -m "Update: main.py에서 신호 생성 로직 수정"

# 3. 로컬에 저장된 최신 버전을 GitHub 서버로 업로드(push)합니다.
git push origin main
3. 다른 컴퓨터에서 다운로드하기 (원격 복제)GitHub에 백업된 Athena_v1 프로젝트를 다른 PC(예: AWS 클라우드 서버)로 그대로 복제해오는 과정입니다.새 컴퓨터에 Git이 설치되어 있는지 확인합니다.프로젝트를 다운로드할 폴더로 터미널을 열고 이동합니다.GitHub 저장소 페이지에서 Code 버튼(초록색)을 누르고 HTTPS 주소(예: https://github.com/my-id/Athena_v1.git)를 복사합니다.터미널에 다음 명령어를 입력합니다.git clone [복사한_HTTPS_주소]
(예: git clone https://github.com/my-id/Athena_v1.git)Athena_v1 폴더가 통째로 다운로드됩니다.중요: 다운로드 후 실행 준비 (필수)GitHub에서 다운로드한 직후에는 3가지 파일/폴더가 없기 때문에 바로 실행되지 않습니다. (.gitignore 때문에 백업에서 제외되었기 때문입니다.)다운로드한 Athena_v1 폴더에서 다음 작업을 수행해야 합니다..env 파일 생성:Athena_v1 폴더 안에 .env 파일을 새로 만듭니다.백업해 둔 실제 업비트 API 키를 이 파일에 입력하고 저장합니다. (가이드 본문 2-2단계: API 키 입력 참고)백엔드 의존성 설치:터미널에서 Athena_v1 폴더로 이동합니다.(가상환경을 사용한다면 python -m venv venv 및 활성화 먼저 수행)pip install -r requirements.txt 를 실행합니다.프론트엔드 의존성 설치 (node_modules):터미널에서 Athena_v1/frontend 폴더로 이동합니다.npm install 을 실행합니다.이 3가지 작업이 완료되면 가이드 본문의 3. 프로그램 실행 단계에 따라 백엔드와 프론트엔드를 실행할 수 있습니다.