#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
judge_api.py — OpenAI ChatGPT API 판정 경로

candidates.json의 각 후보를 ChatGPT로 판정해 agents.csv 스키마의 1행으로
변환하고, agents.csv 끝에 append한 뒤 weekly_report.md에 요약을 남긴다.
score는 LLM이 아니라 grade/maturity/verify 룩업으로 코드가 계산한다(임의 계산 금지).

의존성:  pip install openai
환경변수: OPENAI_API_KEY (필수), MODEL (선택, 기본 gpt-4.1-mini)
사용:     python3 scripts/judge_api.py
"""
import csv
import json
import os
import re
import sys
from datetime import date, timezone, datetime
from openai import OpenAI

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "agents.csv")
CAND_PATH = os.path.join(ROOT, "candidates.json")
REPORT_PATH = os.path.join(ROOT, "weekly_report.md")

MODEL = os.environ.get("MODEL", "gpt-4.1-mini")

# 25컬럼 — 순서 고정(절대 변경 금지). index.html / validate.py와 일치해야 함.
COLUMNS = [
    "id", "category", "subcategory", "name", "type", "features", "openness",
    "nais", "naisuse", "priority", "maturity", "grade", "score", "verify",
    "provider", "provider_group", "released", "released_status", "url",
    "repo_url", "canonical_id", "note", "status", "superseded_by", "last_verified",
]

# LLM이 채우는 필드(나머지는 코드가 결정: id/score/status/last_verified/note 등)
LLM_FIELDS = [
    "category", "subcategory", "name", "type", "features", "openness", "nais",
    "naisuse", "priority", "maturity", "grade", "verify", "provider",
    "provider_group", "released", "released_status", "url", "repo_url",
]

GRADES = ["핵심(즉시)", "관찰(유망·미성숙)", "후보", "참고"]
VERIFY = ["확인완료", "부분확인", "추가검증 필요"]
LEVELS = ["상", "중", "하"]


def today():
    # Actions 러너는 UTC. 날짜만 사용.
    return datetime.now(timezone.utc).date().isoformat()


def score_lookup(grade, maturity, verify):
    """CLAUDE.md §4 룩업표와 동일 규칙. 우선순위대로 처음 맞는 규칙 적용."""
    if verify == "추가검증 필요":
        return 35
    if grade == "참고":
        return 50
    if grade == "관찰(유망·미성숙)":
        return 88 if verify == "확인완료" else 75
    if grade == "후보":
        if verify == "부분확인":
            return 50
        return {"상": 75, "중": 70, "하": 63}.get(maturity, 63)
    if grade == "핵심(즉시)":
        return 100 if maturity == "상" else 95
    return 63


def read_rows():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        rows = list(r)
        header = r.fieldnames
    return header, rows


def next_id(rows):
    mx = 0
    for row in rows:
        m = re.match(r"AG0*(\d+)", (row.get("id") or "").strip())
        if m:
            mx = max(mx, int(m.group(1)))
    return f"AG{mx + 1:03d}"


def existing_keys(rows):
    def norm(s):
        return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

    def nurl(u):
        u = (u or "").strip().lower()
        u = re.sub(r"^https?://", "", u)
        u = re.sub(r"^www\.", "", u)
        return u.rstrip("/")

    names = {norm(r.get("name")) for r in rows}
    urls = set()
    for r in rows:
        for c in ("url", "repo_url"):
            v = nurl(r.get(c))
            if v:
                urls.add(v)
    return names, urls, norm, nurl


SYSTEM = """너는 NAIS의 AI 과학·연구 에이전트 카탈로그 큐레이터다.
후보 정보를 받아 카탈로그 1행으로 만들 판단만 한다. 사실을 날조하지 말고,
불확실하면 보수적으로(낮은 등급, 부분확인, 빈 문자열) 판단한다.
모든 텍스트는 한국어. features는 원문 복붙 금지, 한 문장 요약."""

USER_TMPL = """다음 후보를 평가해 JSON 하나만 출력하라(설명·마크다운 금지).

후보:
- 이름: {name}
- 출처: {source}
- URL: {url}
- 저장소: {repo_url}
- 설명/초록: {summary}
- 공개일: {released}

규칙:
- relevant: 이 후보가 'AI 과학·연구 에이전트'로서 카탈로그에 넣을 가치가 있으면 true, 아니면 false.
- category: 다음 중 하나 — "AI 과학자·자율 연구 Agent", "문헌조사·학술검색 Agent",
  "화학·신약개발·소재 연구 Agent", "바이오·의생명 연구 Agent", "코딩·연구자동화 Agent",
  "Agent 프레임워크·오케스트레이션", "과학 Agent 스킬·로컬 실행 환경", "민간 AI 과학자 플랫폼·FutureHouse Agent군".
- type: "상용 Agent·서비스" / "상용·플랫폼" / "오픈소스 Agent·프로젝트" / "Agent 프레임워크" / "연구논문·프로토타입" 중 하나.
- grade: {grades} 중 하나. 확신 없으면 "후보".
- verify: 기본 "부분확인". 공식 근거로 명확하면 "확인완료".
- priority/maturity: {levels} 중. 확신 없으면 priority="중", maturity="하".
- features: 무엇을 하는 에이전트인지 한 문장 한국어 요약.
- 모르는 값은 빈 문자열 "".

출력 JSON 스키마(정확히 이 키만):
{{"relevant": true/false, "category":"", "subcategory":"", "name":"", "type":"",
"features":"", "openness":"", "nais":"", "naisuse":"", "priority":"", "maturity":"",
"grade":"", "verify":"", "provider":"", "provider_group":"", "released":"",
"released_status":"", "url":"", "repo_url":""}}"""


def call_chatgpt(client, cand):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": USER_TMPL.format(
                    name=cand.get("name", ""),
                    source=cand.get("source", ""),
                    url=cand.get("url", ""),
                    repo_url=cand.get("repo_url", ""),
                    summary=(cand.get("summary", "") or "")[:1500],
                    released=cand.get("released", ""),
                    grades=" / ".join(GRADES),
                    levels=" / ".join(LEVELS),
                ),
            },
        ],
        max_tokens=1200,
        temperature=0.0,
    )
    text = ""
    if response.choices:
        text = response.choices[0].message.content or ""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def sanitize(obj, cand, new_id, tday):
    """LLM 출력 → 검증·보정된 25컬럼 dict."""
    def pick(v, allowed, default):
        v = (v or "").strip()
        return v if v in allowed else default

    row = {c: "" for c in COLUMNS}
    for k in LLM_FIELDS:
        row[k] = (obj.get(k, "") or "").strip()

    # 이름/URL은 후보값으로 보강
    row["name"] = row["name"] or cand.get("name", "")
    row["url"] = row["url"] or cand.get("url", "")
    row["repo_url"] = row["repo_url"] or cand.get("repo_url", "")

    row["grade"] = pick(row["grade"], GRADES, "후보")
    row["verify"] = pick(row["verify"], VERIFY, "부분확인")
    row["priority"] = pick(row["priority"], LEVELS, "중")
    row["maturity"] = pick(row["maturity"], LEVELS, "하")

    row["id"] = new_id
    row["status"] = "active"
    row["canonical_id"] = ""
    row["superseded_by"] = ""
    row["last_verified"] = tday
    row["score"] = str(score_lookup(row["grade"], row["maturity"], row["verify"]))
    ym = tday[:7]
    src = cand.get("source", "auto")
    row["note"] = f"[자동 {ym}] {src} 수집·API 판정"
    return row


def append_rows(header, existing_rows, new_rows):
    """UTF-8 with BOM으로 전체 재작성(헤더 순서 보존)."""
    all_rows = existing_rows + new_rows
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in all_rows:
            w.writerow({c: r.get(c, "") for c in header})


def write_report(added, skipped, tday):
    lines = [
        f"# 주간 카탈로그 갱신 리포트 ({tday})",
        "",
        f"- 판정 경로: OpenAI ChatGPT API (`{MODEL}`)",
        f"- 신규 추가: **{len(added)}건**",
        f"- 제외(관련 없음/중복): {skipped}건",
        "",
    ]
    if added:
        lines.append("## 추가된 항목")
        lines.append("")
        lines.append("| id | 이름 | 대분류 | 등급 | 검증 | score |")
        lines.append("|----|------|--------|------|------|-------|")
        for r in added:
            lines.append(
                f"| {r['id']} | {r['name']} | {r['category']} | {r['grade']} "
                f"| {r['verify']} | {r['score']} |"
            )
    else:
        lines.append("이번 주 신규 추가 항목이 없습니다.")
    lines.append("")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("[error] OPENAI_API_KEY 미설정", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(CAND_PATH):
        print("[info] candidates.json 없음 — 종료(추가 없음)")
        write_report([], 0, today())
        return
    client = OpenAI()

    with open(CAND_PATH, encoding="utf-8") as f:
        candidates = json.load(f)
    if not candidates:
        print("[info] 후보 0건 — 종료")
        write_report([], 0, today())
        return

    header, rows = read_rows()
    names, urls, norm, nurl = existing_keys(rows)
    tday = today()

    added, skipped = [], 0
    seq = 0
    for cand in candidates:
        nn = norm(cand.get("name"))
        nu = nurl(cand.get("url") or cand.get("repo_url"))
        if nn in names or (nu and nu in urls):
            skipped += 1
            continue
        obj = call_chatgpt(client, cand)
        if not obj or not obj.get("relevant"):
            skipped += 1
            continue
        seq += 1
        new_id = f"AG{int(next_id(rows)[2:]) + seq - 1:03d}"
        row = sanitize(obj, cand, new_id, tday)
        added.append(row)
        names.add(norm(row["name"]))
        if nurl(row["url"]):
            urls.add(nurl(row["url"]))
        print(f"  + {row['id']} {row['name']} ({row['grade']}/{row['verify']}, score {row['score']})")

    if added:
        append_rows(header, rows, added)
    write_report(added, skipped, tday)
    print(f"완료: 추가 {len(added)}건, 제외 {skipped}건 → agents.csv, weekly_report.md")


if __name__ == "__main__":
    main()
