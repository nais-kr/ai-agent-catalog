# AI 과학자·연구 에이전트 카탈로그 (NAIS)

NAIS 관점에서 정리한 공개·상용·오픈소스 **AI 과학자/연구 에이전트** 조사 카탈로그입니다.
정적 사이트(GitHub Pages)로 제공되며, 데이터(`agents.csv`)와 화면(`index.html`)이 분리되어 유지보수가 쉽습니다.

- 저장소: <a href="https://github.com/nais-kr/ai-agent-catalog" target="_blank" rel="noopener">nais-kr/ai-agent-catalog</a>
- 사이트: <a href="https://nais-kr.github.io/ai-agent-catalog/" target="_blank" rel="noopener">https://nais-kr.github.io/ai-agent-catalog/</a>
- 데이터: <a href="agents.csv" target="_blank" rel="noopener"><code>agents.csv</code></a> — **이 파일만 수정·푸시하면 사이트가 자동 갱신됩니다.**

## 화면 기능

- 검색(이름·개발사·특징) + 필터(대분류 / 핵심등급 / 검증상태 / 유형)
- 모든 열 정렬(기본: 정렬점수 내림차순), 상단 KPI(전체·핵심·관찰·확인완료)
- 핵심등급·벤치마킹가치·도입성숙도·검증상태 색상 배지, 출처 링크

## 데이터 컬럼(agents.csv)

`id, category, subcategory, name, type, features, openness, nais, naisuse, priority(벤치마킹가치), maturity(도입성숙도), grade(핵심등급), score(정렬점수), verify(검증상태), provider, released, url, note`

- `grade`: 핵심(즉시) / 관찰(유망·미성숙) / 후보 / 참고
- `verify`: 확인완료 / 부분확인 / 추가검증 필요
- `priority`,`maturity`: 상 / 중 / 하

## 업데이트 방법 (GitHub Actions 자동 배포)

1. `agents.csv`를 수정합니다(엑셀/구글시트로 열어 수정 후 CSV로 저장 가능).
2. `main` 브랜치에 커밋/푸시합니다.
3. `.github/workflows/deploy.yml`이 자동 실행되어 GitHub Pages에 재배포합니다.
4. 변경 이력은 Git 커밋으로 자동 보존됩니다. (수동 실행: Actions 탭 → Run workflow)

> 자동 후보 판정 워크플로우는 OpenAI ChatGPT API(`OPENAI_API_KEY`)를 사용하도록 구성되어 있습니다.

## 최초 배포 설정 (1회)

- `nais-kr` 조직에 `ai-agent-catalog` 저장소 생성 후 파일 push
- Settings → Pages → Build and deployment → Source: **GitHub Actions**
- 게시 주소: **<a href="https://nais-kr.github.io/ai-agent-catalog/" target="_blank" rel="noopener">https://nais-kr.github.io/ai-agent-catalog/</a>** (상대경로 기반, 별도 도메인/설정 불필요)

## 주의

- `연구논문·프로토타입` 유형은 성숙도가 낮을 수 있습니다.
- `nais`(관련성)·`priority`·`grade`는 조사 시점의 **잠정 평가**입니다.
