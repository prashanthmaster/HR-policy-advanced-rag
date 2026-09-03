#!/usr/bin/env python3
"""
Corpus coverage audit — the Phase 1 exit criterion, checked rather than claimed.

A probe whose fixture is missing from the corpus does not fail loudly. It passes
vacuously: the system is never asked the hard question, the score looks fine, and
nothing announces the gap. That is the failure this script exists to catch.

Checks, in order:
  1. Every clause in the corpus parses and carries the metadata the pipeline needs.
  2. Every clause referenced by a probe actually exists.
  3. Every corpus requirement (R-nn) is satisfied by a real clause or a recorded
     structural fixture.
  4. Every internal cross-reference points at a clause that exists.
  5. Deliberate absences are still absent.

Standard library only, deliberately: this must run in CI before any dependency
is installed.

Exit 0 = clean. Exit 1 = something to fix.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "corpus")
MAP_FILE = os.path.join(ROOT, "eval", "probe_fixture_map.json")
REQ_FILE = os.path.join(ROOT, "docs", "CORPUS_REQUIREMENTS.md")

REQUIRED_FIELDS = ["country", "doc_type", "effective_date"]
PIPELINE_FIELDS = ["temporal_applicability", "normative", "lineage_id"]
VALID_APPLICABILITY = {
    "POINT_IN_TIME", "SEGMENTED_ACCRUAL", "GRANDFATHERED", "ELECTIVE",
}


def parse_clauses(path):
    """Extract clause metadata blocks. A block runs from a 'clause_id:' line to
    the next '---' fence."""
    clauses = []
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("clause_id:"):
            rec = {"_file": os.path.relpath(path, ROOT), "_line": i + 1}
            j = i
            while j < len(lines) and lines[j].strip() != "---":
                m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$", lines[j])
                if m:
                    rec[m.group(1)] = m.group(2).strip()
                j += 1
            clauses.append(rec)
            i = j
        i += 1
    return clauses


def load_corpus():
    clauses = []
    for dirpath, _dirs, files in os.walk(CORPUS):
        for fn in sorted(files):
            if fn.endswith(".md"):
                clauses.extend(parse_clauses(os.path.join(dirpath, fn)))
    return clauses


def parse_requirements():
    """Pull R-nn identifiers out of the requirements spec."""
    if not os.path.exists(REQ_FILE):
        return set()
    with open(REQ_FILE, encoding="utf-8") as fh:
        return set(re.findall(r"\bR-(\d{2})\b", fh.read()))


def main():
    problems, warnings = [], []

    clauses = load_corpus()
    by_id = {}
    for c in clauses:
        cid = c.get("clause_id")
        if cid in by_id:
            problems.append(
                "duplicate clause_id %r (%s:%d and %s:%d)"
                % (cid, by_id[cid]["_file"], by_id[cid]["_line"],
                   c["_file"], c["_line"])
            )
        by_id[cid] = c

    # 1. metadata completeness
    for c in clauses:
        for f in REQUIRED_FIELDS:
            if f not in c:
                problems.append("%s missing required field %r" % (c.get("clause_id"), f))
        for f in PIPELINE_FIELDS:
            if f not in c:
                warnings.append("%s missing %r (pipeline will need it)" % (c.get("clause_id"), f))
        ta = c.get("temporal_applicability")
        if ta and ta not in VALID_APPLICABILITY:
            problems.append("%s has unknown temporal_applicability %r" % (c.get("clause_id"), ta))

    # 2. probe fixtures exist
    with open(MAP_FILE, encoding="utf-8") as fh:
        pmap = json.load(fh)

    unbacked = []
    for probe, needed in sorted(pmap["probes"].items()):
        if not needed:
            continue
        missing = [n for n in needed if n != "DELIBERATE_ABSENCE" and n not in by_id]
        if missing:
            problems.append("probe %s references missing clauses: %s" % (probe, ", ".join(missing)))
            unbacked.append(probe)

    # 3. requirement coverage
    declared = parse_requirements()
    tagged = set()
    for c in clauses:
        r = c.get("corpus_requirement", "")
        m = re.match(r"R-(\d{2})", r)
        if m:
            tagged.add(m.group(1))
    structural = set()
    for k in pmap.get("requirements_satisfied_by_structure", {}):
        m = re.match(r"R-(\d{2})", k)
        if m:
            structural.add(m.group(1))
    covered = tagged | structural
    uncovered = sorted(n for n in declared if n not in covered)

    # 4. cross-references resolve
    for c in clauses:
        raw = c.get("references", "")
        for ref in re.findall(r"[A-Z][A-Z0-9\-]+", raw):
            if ref not in by_id:
                problems.append("%s references unknown clause %r" % (c.get("clause_id"), ref))
        for field in ("supersedes", "superseded_by", "illustrates"):
            ref = c.get(field, "").strip()
            if ref and ref not in by_id:
                problems.append("%s %s -> unknown clause %r" % (c.get("clause_id"), field, ref))

    # 5. deliberate absences still absent
    #
    # Checked against CLAUSE BODIES only. Editorial notes and defect markers are
    # allowed to name the missing thing - indeed they have to, or nobody knows the
    # gap is deliberate. What must not exist is a *clause* that grants it.
    bodies = ""
    for dirpath, _d, files in os.walk(CORPUS):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            raw = open(os.path.join(dirpath, fn), encoding="utf-8").read()
            raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
            lines = raw.splitlines()
            k = 0
            while k < len(lines):
                if lines[k].startswith("clause_id:"):
                    while k < len(lines) and lines[k].strip() != "---":
                        k += 1
                    k += 1
                    while k < len(lines) and not lines[k].strip().startswith("---"):
                        bodies += lines[k].lower() + "\n"
                        k += 1
                k += 1
    for term in pmap.get("deliberate_absences", []):
        if term.lower() in bodies:
            problems.append(
                "deliberate absence violated: %r appears in a clause body "
                "(see docs/DELIBERATE_DEFECTS.md D-4)" % term
            )

    # ---- report ----
    law = [c for c in clauses if c.get("doc_type") == "law"]
    pol = [c for c in clauses if c.get("doc_type") == "policy"]
    countries = sorted({c.get("country") for c in clauses if c.get("country")})
    scopes = sorted({c.get("jurisdiction_scope") for c in clauses if c.get("jurisdiction_scope")})
    dist = {}
    for c in clauses:
        ta = c.get("temporal_applicability")
        if ta:
            dist[ta] = dist.get(ta, 0) + 1

    print("=" * 62)
    print("CORPUS COVERAGE AUDIT")
    print("=" * 62)
    print("clauses            %d  (%d statutory, %d policy)" % (len(clauses), len(law), len(pol)))
    print("countries          %s" % ", ".join(countries))
    print("jurisdiction scope %s" % ", ".join(scopes))
    print("applicability      %s" % ", ".join("%s=%d" % kv for kv in sorted(dist.items())))
    print("probes mapped      %d" % len(pmap["probes"]))
    print("probes needing no fixture  %d"
          % sum(1 for v in pmap["probes"].values() if not v))
    print("requirements       %d declared, %d covered" % (len(declared), len(covered & declared)))
    print("-" * 62)

    if uncovered:
        print("UNCOVERED REQUIREMENTS: %s" % ", ".join("R-" + n for n in uncovered))
    if warnings:
        print("WARNINGS (%d):" % len(warnings))
        for w in warnings[:12]:
            print("  ~ %s" % w)
        if len(warnings) > 12:
            print("  ~ ... and %d more" % (len(warnings) - 12))
    if problems:
        print("PROBLEMS (%d):" % len(problems))
        for p in problems:
            print("  ! %s" % p)
        print("-" * 62)
        print("RESULT: FAIL")
        return 1

    print("-" * 62)
    if uncovered:
        print("RESULT: FAIL - requirements without a fixture")
        return 1
    print("RESULT: PASS - every probe has a fixture, every requirement a clause")
    return 0


if __name__ == "__main__":
    sys.exit(main())
