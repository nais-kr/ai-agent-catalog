# CLAUDE.md — AI Agent Catalog 자동 큐레이션 지침

이 저장소는 **AI 과학·연구 에이전트 카탈로그**다. 단일 데이터 파일 `agents.csv`를
GitHub Pages(`index.html`)가 읽어 렌더링한다. 이 문서는 매주 자동 큐레이션
(신규 조사·추가·갱신·폐기표기) 시 Claude가 **반드시 따라야 할 판단 규칙**이다.

## 0. 절대 규칙 (위반 시 작업 중단)

- **`agents.csv`의 기존 데이터 행을 절대 삭제하지 마라.** 폐기·중단·대체는
  오직 `status` 컬럼으로만 표시한다(아래 §3 soft-delete).
- **컬럼 순서와 개수(25개)를 절대 바꾸지 마라.** 순서 고정:
  ```
  id, category, subcategory, name, type, features, openness, nais, naisuse,
  priority, maturity, grade, score, verify, provider, provider_group, released,
  released_status, url, repo_url, canonical_id, note, status, superseded_by,
  last_verified
  ```
- **CSV는 UTF-8 with BOM으로 저장**한다(한글 깨짐 방지).
- **사실을 날조하지 마라.** 확인 못 한 값은 빈 문자열로 둔다.
- 저장을 마치면 반드시 `python3 scripts/validate.py`가 통과해야 한다(실패 시 수정).

## 1. 작업 흐름

1. `candidates.json`(collect.py 산출물)을 읽는다. 각 후보는 대략
   `{name, url, source, summary, repo_url?, released?}` 형태다.
2. 각 후보가 기존 `agents.csv`에 이미 있는지 확인한다(이름 또는 URL/repo_url을
   소문자·공백제거로 정규화해 비교). 이미 있으면 새로 추가하지 말고, 새 정보가
   있을 때만 기존 행을 갱신한다(근거가 있을 때만).
3. 진짜 신규 후보만 아래 규칙으로 1행을 만들어 `agents.csv` **맨 끝에 append**한다.
   관련 없는(과학·연구 에이전트가 아닌) 후보는 버린다.
4. `weekly_report.md`에 이번 주 추가/갱신/폐기 항목을 한국어로 요약한다.

## 2. 신규 행 작성 규칙

- **id**: 기존 CSV의 최대 `AGxxx` 번호 + 1, 3자리 zero-pad
  (예: 최대가 AG117이면 다음은 `AG118`, 그다음 `AG119`).
- **status**: `active`.
- **last_verified**: 오늘 날짜 `YYYY-MM-DD`.
- **features**: 초록·소개글을 **자기 표현으로 1문장 한국어 요약**. 원문 복붙 금지.
  무엇을 하는 에이전트인지 드러나게.
- **verify**: 신규 항목 기본은 `부분확인`. 공식 문서/논문으로 명확히 교차확인된
  경우만 `확인완료`. 근거가 빈약하면 `추가검증 필요`.
- **maturity / priority**: 확실치 않으면 **보수적으로** maturity=`하`,
  priority=`중`. 명백한 상용 GA 제품만 `상`.
- **grade**: `벤치마킹가치 × 도입성숙도` 조합.
  - 상용 GA + 도입가치 큼 → `핵심(즉시)`
  - 유망하나 미성숙(연구/베타) → `관찰(유망·미성숙)`
  - 관련 있으나 판단 유보 → `후보`  /  참고 자료 수준 → `참고`
- **type**: 기존 어휘 재사용 — `상용 Agent·서비스` / `상용·플랫폼` /
  `오픈소스 Agent·프로젝트` / `Agent 프레임워크` / `연구논문·프로토타입` 등.
- **canonical_id**: 신규 대표 항목이면 **빈 문자열**. 기존 항목의 중복/이명이면
  대표 행의 id를 넣는다(그러면 KPI 집계에서 제외됨).
- **superseded_by**: 신규 항목은 빈 문자열.
- **provider / provider_group**: 개발사명 / 소속 계열(예: `FutureHouse`, `Google`,
  `OpenAI`). 모르면 빈 문자열.
- **url**: 공식 페이지/논문 링크. **repo_url**: 코드 저장소가 있으면 GitHub 링크.
- **note**: 자동 추가 시 반드시 `[자동 YYYY-MM] <사유/출처>` 형식으로 남긴다.
- 나머지(`subcategory, openness, nais, naisuse, released, released_status`)는
  아는 만큼 채우고 모르면 빈 문자열.

## 3. Soft-delete (폐기·대체 표기)

행을 지우지 말고 `status`로만 표시한다.

- 서비스 종료/중단 → `status=deprecated`, `note`에 `[자동 YYYY-MM] 서비스 종료 …`.
- 다른 항목으로 대체됨 → `status=superseded`, `superseded_by`에 **대체 항목 id**,
  `note`에 `[자동 YYYY-MM] AGxxx로 대체 …`.
- `status` 허용값은 `active` / `deprecated` / `superseded` **세 가지뿐**.

## 4. score 룩업 (임의 계산 금지)

`grade` + `maturity` + `verify` 조합으로 아래 표에서 **정확히** 정한다.
우선순위대로 처음 맞는 규칙을 적용한다.

1. `verify == 추가검증 필요` → **35** (무조건)
2. `grade == 참고` → **50**
3. `grade == 관찰(유망·미성숙)`: verify=확인완료 → **88**, 그 외 → **75**
4. `grade == 후보`: verify=부분확인 → **50**, 아니면 maturity 상 **75** / 중 **70** / 하 **63**
5. `grade == 핵심(즉시)`: maturity=상 → **100**, 그 외 → **95**

## 5. 톤·품질

- 모든 텍스트는 한국어. 과장 금지, 검증 가능한 사실만.
- 불확실하면 항상 **낮은 등급 / 부분확인 / 빈 값** 쪽을 택한다.
- 기존 117행의 내용·표현·컬럼 순서는 건드리지 않는다(신규 append와 명시적
  status 갱신만 허용).
