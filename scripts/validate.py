#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate.py — agents.csv 안전장치 (자동 커밋 전 게이트)

다음 위반 시 exit 1:
  1. 컬럼 순서/개수가 정해진 25개와 정확히 일치하지 않음
  2. git HEAD:agents.csv 대비 기존 id가 하나라도 사라짐 (soft-delete 위반)
  3. status 값이 active/deprecated/superseded 외
  4. 그 밖의 무결성 문제(id 빈값/중복, superseded인데 superseded_by 비었음 등)

이상 없으면 exit 0.
사용: python3 scripts/validate.py
"""
import csv
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "agents.csv")

EXPECTED_COLUMNS = [
    "id", "category", "subcategory", "name", "type", "features", "openness",
    "nais", "naisuse", "priority", "maturity", "grade", "score", "verify",
    "provider", "provider_group", "released", "released_status", "url",
    "repo_url", "canonical_id", "note", "status", "superseded_by", "last_verified",
]
ALLOWED_STATUS = {"active", "deprecated", "superseded"}

errors = []


def fail(msg):
    errors.append(msg)


def read_current():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        rows = list(r)
        return r.fieldnames, rows


def read_head_ids():
    """git HEAD 버전의 id 집합. HEAD에 파일이 없으면 None(첫 도입)."""
    try:
        out = subprocess.run(
            ["git", "show", "HEAD:agents.csv"],
            cwd=ROOT, capture_output=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return None
    text = out.decode("utf-8-sig")
    r = csv.DictReader(io.StringIO(text))
    # HEAD 헤더에 id가 없으면(예: 스키마 변경 직후) 비교 생략
    if not r.fieldnames or "id" not in r.fieldnames:
        return None
    return {(row.get("id") or "").strip() for row in r if (row.get("id") or "").strip()}


def main():
    if not os.path.exists(CSV_PATH):
        print("[FAIL] agents.csv 없음", file=sys.stderr)
        sys.exit(1)

    header, rows = read_current()

    # 1) 컬럼 순서/개수
    if header != EXPECTED_COLUMNS:
        fail(
            "컬럼 스키마 불일치.\n"
            f"  기대({len(EXPECTED_COLUMNS)}): {EXPECTED_COLUMNS}\n"
            f"  실제({len(header) if header else 0}): {header}"
        )
        # 헤더가 어긋나면 이후 검사 무의미 → 즉시 보고
        for e in errors:
            print("[FAIL] " + e, file=sys.stderr)
        sys.exit(1)

    # 2) soft-delete: HEAD id가 사라지지 않았는지
    head_ids = read_head_ids()
    cur_ids = [(r.get("id") or "").strip() for r in rows]
    cur_id_set = set(cur_ids)
    if head_ids is not None:
        missing = head_ids - cur_id_set
        if missing:
            fail(
                "soft-delete 위반: 이전 버전 대비 사라진 id "
                f"{sorted(missing)} — 삭제 대신 status=deprecated/superseded 사용."
            )

    # 3) status 값
    for i, r in enumerate(rows, start=2):  # 2 = 헤더 다음 줄
        st = (r.get("status") or "").strip()
        if st not in ALLOWED_STATUS:
            fail(f"{i}행(id={r.get('id')!r}) status 값 오류: {st!r}")

    # 4) 기타 무결성
    seen = set()
    for i, r in enumerate(rows, start=2):
        rid = (r.get("id") or "").strip()
        if not rid:
            fail(f"{i}행: id가 비어 있음")
            continue
        if rid in seen:
            fail(f"{i}행: id 중복 {rid!r}")
        seen.add(rid)
        if (r.get("status") or "").strip() == "superseded" and not (r.get("superseded_by") or "").strip():
            fail(f"{i}행(id={rid}): status=superseded인데 superseded_by 비어 있음")

    if errors:
        for e in errors:
            print("[FAIL] " + e, file=sys.stderr)
        print(f"\n검증 실패: {len(errors)}건", file=sys.stderr)
        sys.exit(1)

    added = (len(cur_id_set) - len(head_ids)) if head_ids is not None else 0
    print(
        f"[OK] 검증 통과 — {len(rows)}행, 25컬럼, status 정상"
        + (f", 신규 {added}건" if added else "")
    )


if __name__ == "__main__":
    main()
