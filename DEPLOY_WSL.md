# WSL(Ubuntu) + VSCode 배포 가이드 — nais-kr/ai-agent-catalog

이 사이트(`ai-agent-catalog`)를 `nais-kr` 조직의 GitHub 저장소로 올리고,
GitHub Actions로 자동 배포(GitHub Pages)까지 설정하는 방법입니다.

Windows 원본 위치: `C:\Users\gooroom\Claude\Projects\NAIS 업무\ai-agent-catalog`
WSL에서의 경로:    `/mnt/c/Users/gooroom/Claude/Projects/NAIS 업무/ai-agent-catalog`
작업 위치(권장):    프로젝트 루트 `~/workspace/nais` 아래 `~/workspace/nais/ai-agent-catalog`

> WSL 홈(`~`) 아래에서 작업하면 한글/공백 경로 문제와 Windows-WSL 파일 성능 저하를 피할 수 있습니다.

---

## A. 사전 준비 (최초 1회)

WSL Ubuntu 터미널에서:

```bash
# git, GitHub CLI 설치
sudo apt update
sudo apt install -y git
type gh >/dev/null 2>&1 || (curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  | sudo tee /etc/apt/sources.list.d/github-cli.list \
  && sudo apt update && sudo apt install -y gh)

# GitHub 로그인 (브라우저 인증)
gh auth login          # GitHub.com → HTTPS → Login with a web browser

# git 사용자 정보 (아직 안 했다면)
git config --global user.name  "본인이름"
git config --global user.email "ymkang@nst.re.kr"
```

> `nais-kr` 조직에 저장소를 만들려면 해당 조직에 대한 권한이 있어야 합니다.
> `gh auth login` 시 조직 접근 권한(scope)을 허용하세요.

---

## B. 워크스페이스에 프로젝트 폴더 만들고 업로드

```bash
# 1) 워크스페이스 아래 프로젝트 폴더 준비 (원본을 그대로 복사해 옴)
mkdir -p ~/workspace/nais
cp -r "/mnt/c/Users/gooroom/Claude/Projects/NAIS 업무/ai-agent-catalog" ~/workspace/nais/ai-agent-catalog
cd ~/workspace/nais/ai-agent-catalog

# 2) git 초기화 및 첫 커밋
git init -b main
git add .
git commit -m "init: AI 과학자·연구 에이전트 카탈로그 (117개)"

# 3) 조직 저장소 생성 + 푸시 (한 번에)
gh repo create nais-kr/ai-agent-catalog --public --source=. --remote=origin --push

# 4) GitHub Pages를 'GitHub Actions' 소스로 활성화
gh api -X POST repos/nais-kr/ai-agent-catalog/pages -f build_type=workflow

# 5) 배포 워크플로 실행 확인
gh run watch
```

배포 완료 후 주소: **https://nais-kr.github.io/ai-agent-catalog/**
(첫 배포는 1~2분 정도 소요될 수 있습니다.)

> VSCode로 이 폴더를 열려면: `code ~/workspace/nais/ai-agent-catalog`
> (VSCode에서 WSL 확장 설치 후 좌하단 초록 아이콘 → "Connect to WSL" 상태여야 합니다.)

---

## C. 이후 업데이트 (반복)

`agents.csv`만 고치고 push하면 Actions가 자동 재배포합니다.

```bash
cd ~/workspace/nais/ai-agent-catalog

# (엑셀에서 CSV로 다시 저장했다면 원본을 덮어쓰기 복사)
# cp "/mnt/c/Users/gooroom/Claude/Projects/NAIS 업무/ai-agent-catalog/agents.csv" ./agents.csv

git add -A
git commit -m "update: 에이전트 목록 갱신"
git push
gh run watch     # 배포 진행 상황 확인 (선택)
```

VSCode에서 하려면: 이 폴더를 연 뒤 Source Control(Ctrl+Shift+G)에서
스테이지 → 커밋 → 동기화(Push) 하면 동일하게 자동 배포됩니다.

---

## D. VSCode AI 어시스턴트용 프롬프트 (복사해서 사용)

VSCode의 Claude Code / Copilot Chat(Agent 모드) 터미널에 아래를 그대로 붙여넣으세요.

```
WSL Ubuntu 환경입니다. 아래 작업을 순서대로 수행해줘. 각 단계 명령을 실행하고 결과를 확인한 뒤 다음으로 진행해.

목표: 정적 사이트를 WSL 워크스페이스 하위 폴더에서 작업해 nais-kr 조직의 GitHub 저장소(ai-agent-catalog)로
올리고, GitHub Actions 기반 GitHub Pages로 자동 배포되게 설정한다.

전제:
- Windows 원본: "/mnt/c/Users/gooroom/Claude/Projects/NAIS 업무/ai-agent-catalog"
  (index.html, agents.csv, README.md, .github/workflows/deploy.yml 포함)
- 작업 폴더: ~/workspace/nais/ai-agent-catalog  (워크스페이스 하위 프로젝트 폴더)
- 저장소: nais-kr/ai-agent-catalog (public), 게시 주소: https://nais-kr.github.io/ai-agent-catalog/

수행 단계:
1. git, gh(GitHub CLI) 설치 여부 확인하고 없으면 설치.
2. `gh auth status`로 로그인 확인, 안 돼 있으면 `gh auth login` 안내(웹 인증, 조직 권한 포함).
3. `mkdir -p ~/workspace/nais` 후 Windows 원본을 ~/workspace/nais/ai-agent-catalog 로 복사하고 그 경로로 이동.
4. git 저장소 초기화(main 브랜치), 전체 add, "init" 커밋.
5. `gh repo create nais-kr/ai-agent-catalog --public --source=. --remote=origin --push` 로 생성+푸시.
6. `gh api -X POST repos/nais-kr/ai-agent-catalog/pages -f build_type=workflow` 로 Pages를 Actions 소스로 활성화.
7. `gh run watch`로 배포 완료 확인 후, 최종 URL을 알려줘.
8. 문제가 생기면 원인과 해결책을 설명하고 멈춰서 물어봐.

주의: 원본 경로에 공백/한글이 있으니 반드시 따옴표로 감싸라. 파괴적 명령(rm -rf 등)은 쓰지 마라.
```

---

## 자주 겪는 문제

- **권한 오류(403)**: `nais-kr` 조직 멤버/권한 확인. `gh auth refresh -s admin:org` 후 재시도.
- **Pages 활성화 실패**: 웹에서 Settings → Pages → Source를 "GitHub Actions"로 수동 설정해도 됩니다.
- **한글/공백 경로 에러**: 경로를 항상 큰따옴표로 감싸거나, 워크스페이스(`~/workspace/...`)로 복사 후 작업.
- **줄바꿈(CRLF) 경고**: `git config --global core.autocrlf input` 권장.
