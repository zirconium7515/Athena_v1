Athena v1 사용 가이드 (2. GitHub 백업편)이 가이드는 Athena v1 프로젝트를 GitHub(깃헙)에 백업(업로드)하고, 코드를 수정한 뒤 업데이트하며, 다른 PC에서 다운로드하는 방법을 안내합니다.[A] GitHub 저장소 생성 (최초 1회)GitHub에 로그인합니다.New 버튼을 눌러 새 저장소(Repository)를 생성합니다.저장소 이름을 Athena_v1 (권장)로 정합니다.(중요) Add a README file 옵션을 체크 해제합니다. (로컬에서 이미 README.md가 있거나, 나중에 올릴 것이므로)Public (공개) 또는 Private (비공개)를 선택합니다. (코드를 비공개로 하려면 Private 선택)Create repository 버튼을 누릅니다.생성된 저장소 페이지에서 https://github.com/YourUsername/Athena_v1.git 형태의 주소(URL)를 복사해 둡니다.[B] 로컬 프로젝트 업로드 (최초 1회)Athena_v1 프로젝트 폴더의 터미널에서 다음 명령어들을 순서대로 실행합니다.# (위치: Athena_v1)

# 1. 이 폴더를 Git 저장소로 초기화
git init -b main

# 2. GitHub 저장소 주소(URL)를 'origin'이라는 이름으로 연결
# (주의: "YourUsername" 부분을 실제 GitHub 이름으로 변경)
git remote add origin [https://github.com/YourUsername/Athena_v1.git](https://github.com/YourUsername/Athena_v1.git)

# 3. 모든 파일을 Git 추적 대상으로 추가 (단, .gitignore에 명시된 파일 제외)
git add .

# 4. 'Initial commit'이라는 이름으로 변경사항을 저장(커밋)
git commit -m "Initial commit of Athena v1 project"

# 5. 로컬 저장소(main)의 내용을 GitHub(origin)으로 강제 푸시(업로드)
# (주의: --force는 GitHub의 초기 상태를 덮어쓰므로, 최초 1회만 사용 권장)
git push -u origin main --force
[C] 수정된 코드 업데이트 (반복 작업)main.py를 수정했거나 ai_trader/ 폴더의 파일을 수정한 뒤, GitHub에 변경 내역을 백업(업데이트)하는 방법입니다.# (위치: Athena_v1)

# 1. 수정된 모든 파일 추가
git add .

# 2. 어떤 변경사항인지 메시지를 남기며 저장(커밋)
# (예: "API 키 입력 기능 GUI에 추가")
git commit -m "여기에 변경 내용 요약"

# 3. GitHub(origin)으로 변경사항 업로드(푸시)
git push origin main
[D] 다른 PC에서 다운로드 (Clone)다른 컴퓨터(또는 서버)에서 GitHub에 백업된 Athena_v1 프로젝트를 다운로드하는 방법입니다.# (위치: 코드를 다운로드할 폴더)

# 1. GitHub 저장소 주소(URL)로 프로젝트 전체를 복제(다운로드)
# (주의: "YourUsername" 부분을 실제 GitHub 이름으로 변경)
git clone [https://github.com/YourUsername/Athena_v1.git](https://github.com/YourUsername/Athena_v1.git)

# 2. 다운로드된 Athena_v1 폴더로 이동
cd Athena_v1
다운로드 후에는 사용가이드_1_설치.md 가이드의 2. 설치 및 설정부터 다시 진행하시면 됩니다.[부록 A: 문제 해결][문제 1] .gitignore가 작동하지 않고 캐시 파일(__pycache__ 등)이 계속 추적될 때원인: .gitignore 파일을 수정하기 전에 git add .를 실행하여, Git이 이미 해당 파일들을 '추적'하겠다고 **기억(캐시)**해버렸기 때문입니다.해결책: Git의 기억(캐시)을 강제로 삭제하고, 수정된 .gitignore 규칙에 따라 파일들을 다시 추가해야 합니다.# (위치: Athena_v1)

# 1. Git의 추적 목록(캐시)을 모두 삭제
git rm -r --cached .

# 2. 새 .gitignore 규칙에 따라 파일 다시 추가
git add .

# 3. 캐시 정리 내역을 저장(커밋)
git commit -m "Fix: .gitignore 규칙 적용 및 캐시 파일 정리"

# 4. GitHub에 업로드(푸시)
git push origin main
[문제 2] git push 실행 시 [rejected] (fetch first) 오류가 발생할 때원인: GitHub 저장소(Remote)에 고객님의 PC(Local)에 없는 변경 내역(커밋)이 존재하기 때문입니다. (예: GitHub에서 README.md 파일을 직접 수정했거나, 다른 PC에서 push한 경우)해결책 1 (권장): GitHub의 변경 내역을 먼저 가져오기 (Pull)# 1. GitHub(origin)의 변경 사항을 로컬(main)로 가져와 합칩니다(pull).
git pull origin main

# 2. (충돌(conflict)이 없다면) 다시 푸시합니다.
git push origin main
해결책 2 (위험): GitHub의 변경 내역을 무시하고 강제로 덮어쓰기 (Force Push)(주의: 이 방법은 GitHub의 기존 내역을 삭제하므로, 협업 시 절대 사용하면 안 됩니다. 혼자 쓰는 저장소이고 GitHub 내역이 필요 없을 때만 사용하세요.)git push origin main --force
