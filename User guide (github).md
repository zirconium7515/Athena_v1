Athena v1 - GitHub 백업 및 관리 가이드이 문서는 Athena_v1 프로젝트를 GitHub에 새로 백업(업로드)하고, 변경 사항을 업데이트하며, 다른 컴퓨터에 다운로드(복제)하는 방법을 설명합니다.0. 사전 준비 사항Git 설치: 이 모든 작업을 수행하려면 컴퓨터에 Git이 설치되어 있어야 합니다. (https://git-scm.com/downloads/)GitHub 계정: GitHub 웹사이트(https://www.google.com/search?q=https://github.com/)%EC%97%90%EC%84%9C 계정을 생성해야 합니다.1. 새 프로젝트 GitHub에 처음 업로드하기 (백업)로컬 컴퓨터에 있는 Athena_v1 폴더 전체를 GitHub에 새로 백업하는 과정입니다.1단계: GitHub에서 새 저장소(Repository) 생성GitHub 웹사이트에 로그인합니다.우측 상단의 + 아이콘을 클릭한 후, New repository를 선택합니다.Repository name에 Athena_v1 (또는 원하시는 다른 이름)을 입력합니다.Public (공개) 또는 Private (비공개)를 선택합니다.(권장) Private를 선택하세요. API 키 등 민감한 정보가 실수로 노출되는 것을 막기 위해 비공개로 설정하는 것이 좋습니다.중요: Add a README file, Add .gitignore, Choose a license 항목은 모두 체크 해제한 상태로 둡니다. (이미 로컬에 파일들이 있기 때문입니다)Create repository 버튼을 클릭합니다.2단계: 터미널에서 로컬 프로젝트 업로드PC에서 터미널(명령 프롬프트)을 엽니다.Athena_v1 루트 폴더로 이동합니다.cd 경로/Athena_v1
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
(예: git clone https://github.com/my-id/Athena_v1.git)Athena_v1 폴더가 통째로 다운로드됩니다.중요: 다운로드 후 실행 준비 (필수)GitHub에서 다운로드한 직후에는 3가지 파일/폴더가 없기 때문에 바로 실행되지 않습니다. (.gitignore 때문에 백업에서 제외되었기 때문입니다.)다운로드한 Athena_v1 폴더에서 다음 작업을 수행해야 합니다..env 파일 생성:Athena_v1 폴더 안에 .env 파일을 새로 만듭니다.백업해 둔 실제 업비트 API 키를 이 파일에 입력하고 저장합니다. (기존 사용가이드.md 2-1단계 참고)백엔드 의존성 설치:터미널에서 Athena_v1 폴더로 이동합니다.pip install -r requirements.txt 를 실행합니다.프론트엔드 의존성 설치 (node_modules):터미널에서 Athena_v1/frontend 폴더로 이동합니다.npm install 을 실행합니다.이 3가지 작업이 완료되면 사용가이드_1_설치.md의 3. 프로그램 실행 단계에 따라 백엔드와 프론트엔드를 실행할 수 있습니다.[부록 A: 문제 해결][문제 해결] .gitignore가 작동하지 않고 캐시 파일이 계속 추적될 때문제: .gitignore에 __pycache__/나 *.log를 추가했는데도 git add .를 하면 해당 파일들이 계속 GitHub에 포함됩니다.원인: .gitignore를 수정하기 전에 이미 git add .를 실행해서, Git이 "이 파일들을 추적해야 한다"라고 기억(캐시)해 버렸기 때문입니다.해결책: Git이 기억하고 있는 추적 목록(캐시)을 강제로 삭제한 뒤, 수정된 .gitignore 규칙에 따라 파일들을 다시 추가해야 합니다.(위치: Athena_v1 폴더의 터미널)1단계: Git 캐시(기억) 삭제(실제 파일이 아닌, Git의 추적 목록만 삭제합니다.)git rm -r --cached .
2단계: 파일 다시 추가(새 .gitignore 규칙이 적용되어, 무시 대상 파일들이 제외됩니다.)git add .
3단계: 캐시 정리 내역 저장(Commit)git commit -m "Fix: .gitignore 규칙 적용 및 캐시 파일 정리"
4단계: GitHub에 업로드(Push)git push origin main
[문제 해결] git push가 [rejected] (fetch first) 오류로 실패할 때문제: git push -u origin main 실행 시 ! [rejected] main -> main (fetch first) 오류가 발생합니다.원인: GitHub 저장소(Remote)에 고객님의 PC(Local)에 없는 변경 내역(커밋)이 존재하기 때문입니다. (예: GitHub에서 저장소를 만들 때 README 파일을 함께 생성한 경우)해결책: PC에 있는 Athena_v1 코드가 가장 최신 버전이므로, GitHub의 기존 내역을 무시하고 PC 버전으로 강제로 덮어씁니다.(위치: Athena_v1 폴더의 터미널)git push origin main --force
(주의): --force 옵션은 GitHub의 내용을 강제로 덮어쓰므로, 지금처럼 처음 백업을 업로드할 때 또는 덮어쓸 내용이 확실할 때만 사용해야 합니다.