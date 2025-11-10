Athena v1 - GitHub 가이드 (부록)이 문서는 Athena_v1 프로젝트를 GitHub에 백업하고 관리하는 방법을 설명합니다.[부록 A: GitHub 가이드]1. 새 프로젝트 GitHub에 처음 업로드하기 (백업)GitHub에서 새 저장소(Repository) 생성:GitHub 로그인 후, New repository를 생성합니다.Repository name (예: Athena_v1)을 입력합니다.(권장) Private (비공개)로 설정합니다.체크박스(README, .gitignore)는 모두 해제하고 Create repository를 클릭합니다.터미널에서 로컬 프로젝트 업로드:Athena_v1 루트 폴더에서 터미널을 엽니다.아래 명령어들을 순서대로 실행합니다. (GitHub에서 안내해 주는 …or push an existing repository 명령어와 동일합니다)# (위치: Athena_v1)
git init
git branch -M main

# [YOUR_USERNAME]과 [REPOSITORY_NAME]을 실제 정보로 바꿔야 합니다.
git remote add origin [https://github.com/](https://github.com/)[YOUR_USERNAME]/[REPOSITORY_NAME].git

git add .
git commit -m "Initial commit: Athena v1"
git push -u origin main
2. 변경된 코드 업데이트하기 (수정 사항 반영)코드를 수정한 후(예: main.py 파일 수정), 변경된 내용을 GitHub 백업에 덮어쓰는(업데이트) 과정입니다.# (위치: Athena_v1)
# 1. 수정된 모든 파일을 Git에 알림
git add .

# 2. 수정 내역을 메시지로 남기고 로컬에 저장(commit)
git commit -m "Update: [수정한 내용 요약]"

# 3. 로컬 변경 사항을 GitHub 서버로 업로드(push)
git push origin main
3. 다른 컴퓨터에서 다운로드하기 (원격 복제)GitHub에 백업된 Athena_v1 프로젝트를 다른 PC(예: AWS 클라우드 서버)로 그대로 복제해오는 과정입니다.GitHub 저장소 페이지에서 Code 버튼(초록색)을 누르고 HTTPS 주소를 복사합니다.새 컴퓨터의 터미널에 다음 명령어를 입력합니다.git clone [복사한_HTTPS_주소]
(예: git clone https://github.com/my-id/Athena_v1.git)다운로드 후 실행 준비 (필수):git clone 직후에는 .env 파일과 라이브러리 폴더(venv, node_modules)가 없으므로, 반드시 이 가이드의 2. 설치 및 설정 1~4단계를 다시 수행해야 합니다. (API 키 복사, pip install, npm install)[문제 해결] .gitignore가 작동하지 않고 캐시 파일이 계속 추적될 때문제:.gitignore 파일을 수정(예: __pycache__/ 추가)했는데도, git status에 __pycache__ 폴더나 .db 파일 등이 계속 추적 대상(Staged)으로 잡힙니다.원인:.gitignore 파일을 수정하거나 추가하기 전에 이미 git add . 명령어를 실행해서, Git이 "이 캐시 파일들을 추적해야 한다"라고 기억(Caching)해버렸기 때문입니다.해결 방법 (Git 캐시 삭제):우선, 수정된 .gitignore 파일이 올바르게 저장되었는지 확인합니다.Athena_v1 루트 폴더의 터미널에서 다음 명령어를 실행하여, Git의 캐시(기억)만 삭제합니다. (로컬 파일은 삭제되지 않습니다.)# (위치: Athena_v1)
git rm -r --cached .
rm -r --cached . : 현재 폴더(.)의 모든 파일에 대해, Git의 추적(cached)을 제거(-r)합니다.이제 Git이 깨끗한 상태가 되었으므로, 수정된 .gitignore 규칙을 적용하여 모든 파일을 다시 추가(Re-add)합니다.# (위치: Athena_v1)
git add .
(이제 __pycache__나 .env 등은 무시됩니다.)캐시가 정리되었다는 내역을 저장(commit)합니다.# (위치: Athena_v1)
git commit -m "Fix: .gitignore 규칙 적용 및 캐시 파일 정리"
정리된 내역을 GitHub로 업로드(push)합니다.# (위치: Athena_v1)
git push origin main
