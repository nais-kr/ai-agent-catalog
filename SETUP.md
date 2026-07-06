# SETUP.md — 주간 자동 갱신 시스템 설치·운영 가이드

이 저장소는 매주 **자동 수집 → 검토(판정) → 적용**으로 AI 과학·연구 에이전트
카탈로그(`agents.csv`)를 유지한다. 이 문서는 그 시스템을 켜고 운영하는 방법이다.

## 1. 파일 구성

```
ai-agent-catalog/
├── agents.csv                          # 데이터(25컬럼, UTF-8 BOM) — 유일한 원본
├── index.html                          # GitHub Pages 화면 (agents.csv를 fetch)
├── CLAUDE.md                           # 자동 큐레이션 판단 지침(구독 경로가 읽음)
├── candidates.json                     # collect.py 산출물(주간 후보) — 자동 생성
├── weekly_report.md                    # 주간 갱신 요약 — 자동 생성
├── scripts/
│   ├── collect.py                      # arXiv·GitHub 후보 수집(LLM 없음, 표준 라이브러리)
│   ├── judge_api.py                    # Claude API 폴백(후보→CSV 행)
│   └── validate.py                     # 안전장치(컬럼/soft-delete/status 검증)
└── .github/workflows/
    ├── deploy.yml                      # push 시 GitHub Pages 배포
    └── weekly-catalog-update.yml       # 매주 월요일 자동 갱신
```

## 2. 판정 경로 두 가지

워크플로우는 시크릿 유무로 자동 분기한다(구독 우선).

| 경로 | 필요 시크릿 | 방식 | 비용 |
|------|-------------|------|------|
| **구독(권장)** | `CLAUDE_CODE_OAUTH_TOKEN` | `claude-code-action`이 CLAUDE.md 지침대로 큐레이션 | Claude 구독에 포함 |
| **API 폴백** | `ANTHROPIC_API_KEY` | `judge_api.py`가 Haiku로 후보를 행으로 변환 | 사용량 과금(소액) |
| 없음 | — | 수집만 하고 판정 건너뜀(경고) | 무료 |

> 둘 다 있으면 **구독 경로**를 쓴다. 공개 저장소이므로 GitHub Actions 실행은 무료다.

## 3. 시크릿 등록

저장소 → **Settings → Secrets and variables → Actions → New repository secret**

### (A) 구독 토큰 — `CLAUDE_CODE_OAUTH_TOKEN` (권장)

로컬에 Claude Code가 설치된 상태에서:

```bash
claude setup-token
```

출력된 토큰을 `CLAUDE_CODE_OAUTH_TOKEN` 시크릿으로 등록한다.
(Claude Pro/Max 구독 계정으로 로그인되어 있어야 한다.)

### (B) API 키 — `ANTHROPIC_API_KEY` (폴백)

<https://console.anthropic.com> → API Keys에서 발급 → 같은 이름으로 등록.
구독 토큰을 넣었다면 없어도 되지만, 폴백으로 함께 넣어두면 안전하다.

### (C) GitHub App 설치 (구독 경로 사용 시)

`claude-code-action`은 GitHub App으로 동작한다. 최초 1회:

1. <https://github.com/apps/claude> 에서 **Claude GitHub App**을 이 저장소에 설치.
2. 저장소 **Settings → Actions → General → Workflow permissions**에서
   **Read and write permissions** 활성화(PR·커밋 생성 허용).

## 4. GitHub Pages 설정 (1회)

**Settings → Pages → Build and deployment → Source: GitHub Actions**
게시 주소: <https://nais-kr.github.io/ai-agent-catalog/>
(`agents.csv`가 갱신되어 main에 반영되면 `deploy.yml`이 자동 재배포한다.)

## 5. 실행 방법

### 자동
- 매주 **월요일 00:00 UTC(09:00 KST)** 에 `weekly-catalog-update.yml`이 실행된다.

### 수동
- 저장소 **Actions → Weekly Catalog Update → Run workflow**.
- `auto_merge` 체크 시 PR 없이 main 직접 커밋(아래 §7).

### 로컬에서 점검
```bash
python3 scripts/collect.py            # candidates.json 생성
ANTHROPIC_API_KEY=sk-... python3 scripts/judge_api.py   # (선택) API로 판정 테스트
python3 scripts/validate.py           # 안전장치 통과 여부
```

## 6. Soft-delete 운영 (행 삭제 금지)

- 에이전트가 사라져도 **행을 지우지 않는다.** `status` 컬럼으로만 표시한다.
  - 서비스 종료 → `status=deprecated`
  - 다른 항목으로 대체 → `status=superseded` + `superseded_by`에 대체 id
- `validate.py`가 이전 버전 대비 **id가 사라지면 실패(exit 1)** 시켜 자동 삭제를 막는다.
- 화면(index.html)에서는 해당 행이 **취소선 + 상태 뱃지**로 표시되고 목록에는 남는다.
- KPI 합계는 `canonical_id`가 빈 행(중복 아님)만 집계한다.

## 7. 완전 무인 전환 (PR 없이 main 직접 커밋)

기본은 **PR을 생성**해 사람이 검토 후 머지한다. 검토 없이 바로 반영하려면:

- **수동 실행 시**: Run workflow에서 `auto_merge`를 체크.
- **항상 무인으로**: `weekly-catalog-update.yml`의 마지막 스텝 `AUTO_MERGE` 기본값을
  `'true'`로 바꾸거나, `on.schedule` 실행에서도 직접 커밋하도록
  `AUTO_MERGE: 'true'`를 env에 고정한다.

> ⚠️ 무인 모드에서도 `validate.py` 게이트는 항상 먼저 통과해야 커밋된다
> (컬럼 변경·행 삭제·잘못된 status는 커밋 자체가 차단됨).

## 8. 비용 요약

| 항목 | 비용 |
|------|------|
| GitHub Actions (공개 저장소) | 무료 |
| GitHub Pages | 무료 |
| arXiv / GitHub API 수집 | 무료 |
| 구독 경로(`CLAUDE_CODE_OAUTH_TOKEN`) | Claude 구독료에 포함(추가 과금 없음) |
| API 폴백(`ANTHROPIC_API_KEY`, Haiku) | 후보 수십 건 판정 시 주당 수 센트 수준 |

## 9. 문제 해결

- **판정이 건너뛰어짐**: 시크릿 미등록. §3에서 토큰/키 등록.
- **PR이 안 생김**: Workflow permissions가 read-only. §3(C) 2번 확인.
- **validate 실패로 중단**: 로그의 `[FAIL]` 메시지 확인. 대개 컬럼 순서 변경 또는
  행 삭제 시도. `agents.csv`를 스키마에 맞게 되돌린다.
- **한글 깨짐**: CSV는 반드시 **UTF-8 with BOM**으로 저장(스크립트는 이미 준수).
