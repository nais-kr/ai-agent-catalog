#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect.py — 신규 AI 과학·연구 에이전트 후보 수집기 (LLM 없음, 표준 라이브러리만)

arXiv API와 GitHub Search API를 조회해, 기존 agents.csv에 없는 후보만
이름·URL 기준으로 중복 제거하여 candidates.json으로 저장한다.
판단·평가는 하지 않는다(수집만). 실제 CSV 행 변환은 judge 단계(judge_api.py)가 담당한다.

사용:
  python3 scripts/collect.py                 # 기본 수집
  MAX_CANDIDATES=40 python3 scripts/collect.py
환경변수:
  GITHUB_TOKEN     (선택) GitHub API rate limit 완화용
  MAX_CANDIDATES   (선택) 후보 최대 개수, 기본 30
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "agents.csv")
OUT_PATH = os.path.join(ROOT, "candidates.json")

MAX_CANDIDATES = int(os.environ.get("MAX_CANDIDATES", "30"))
UA = "nais-ai-agent-catalog-collector/1.0 (+https://github.com/nais-kr/ai-agent-catalog)"

# arXiv 검색 쿼리 — 과학·연구 에이전트 관련
ARXIV_QUERIES = [
    'all:"AI scientist" AND (cat:cs.AI OR cat:cs.LG)',
    'all:"autonomous research agent"',
    'all:"scientific discovery agent"',
    'all:"multi-agent" AND all:"research automation"',
    'all:"LLM agent" AND all:"literature review"',
]

# GitHub 저장소 검색 쿼리
GITHUB_QUERIES = [
    "AI scientist agent research",
    "autonomous research agent LLM",
    "scientific discovery agent",
    "multi-agent research framework",
]


def _norm(s):
    """이름/URL 비교용 정규화: 소문자, 영숫자만."""
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _norm_url(u):
    """URL 비교용 정규화: scheme·www·trailing slash 제거."""
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")


def load_existing():
    """기존 agents.csv에서 중복 판정용 이름/URL 집합을 만든다."""
    names, urls = set(), set()
    if not os.path.exists(CSV_PATH):
        return names, urls
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("name"):
                names.add(_norm(row["name"]))
            for col in ("url", "repo_url"):
                v = _norm_url(row.get(col, ""))
                if v:
                    urls.add(v)
    return names, urls


def _get(url, headers=None, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    print(f"  [warn] 요청 실패({url[:60]}…): {last}", file=sys.stderr)
    return None


def fetch_arxiv(query, max_results=10):
    base = "http://export.arxiv.org/api/query?"
    q = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    data = _get(base + q)
    if not data:
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []
    for e in root.findall("a:entry", ns):
        title = (e.findtext("a:title", default="", namespaces=ns) or "").strip()
        title = re.sub(r"\s+", " ", title)
        summary = (e.findtext("a:summary", default="", namespaces=ns) or "").strip()
        summary = re.sub(r"\s+", " ", summary)
        link = (e.findtext("a:id", default="", namespaces=ns) or "").strip()
        published = (e.findtext("a:published", default="", namespaces=ns) or "")[:10]
        if title and link:
            out.append(
                {
                    "name": title,
                    "url": link,
                    "repo_url": "",
                    "source": "arxiv",
                    "summary": summary[:600],
                    "released": published,
                }
            )
    time.sleep(3)  # arXiv API 예의상 간격
    return out


def fetch_github(query, per_page=10):
    base = "https://api.github.com/search/repositories?"
    q = urllib.parse.urlencode(
        {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
    )
    headers = {"Accept": "application/vnd.github+json"}
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    data = _get(base + q, headers=headers)
    if not data:
        return []
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return []
    out = []
    for it in payload.get("items", []):
        name = it.get("name") or ""
        full = it.get("full_name") or name
        out.append(
            {
                "name": full,
                "url": it.get("homepage") or it.get("html_url", ""),
                "repo_url": it.get("html_url", ""),
                "source": "github",
                "summary": (it.get("description") or "")[:600],
                "released": (it.get("created_at") or "")[:10],
                "stars": it.get("stargazers_count", 0),
            }
        )
    time.sleep(2)  # GitHub search rate limit 배려
    return out


def main():
    names, urls = load_existing()
    print(f"기존 카탈로그: 이름 {len(names)}개, URL {len(urls)}개 로드")

    raw = []
    print("arXiv 조회 중…")
    for q in ARXIV_QUERIES:
        raw += fetch_arxiv(q)
    print("GitHub 조회 중…")
    for q in GITHUB_QUERIES:
        raw += fetch_github(q)

    # 중복 제거: 기존 카탈로그 + 이번 수집 내부 중복
    seen_name, seen_url = set(), set()
    candidates = []
    for c in raw:
        nn, nu = _norm(c["name"]), _norm_url(c.get("url") or c.get("repo_url"))
        if not nn:
            continue
        if nn in names or (nu and nu in urls):
            continue  # 이미 카탈로그에 존재
        if nn in seen_name or (nu and nu in seen_url):
            continue  # 이번 수집 내 중복
        seen_name.add(nn)
        if nu:
            seen_url.add(nu)
        candidates.append(c)
        if len(candidates) >= MAX_CANDIDATES:
            break

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    print(f"수집 완료: 원본 {len(raw)}건 → 신규 후보 {len(candidates)}건")
    print(f"저장: {OUT_PATH}")


if __name__ == "__main__":
    main()
