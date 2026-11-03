"""Builds README.md for a LeetCode solutions repo.

Groups every solution file by language, then by difficulty (Easy / Medium / Hard).
Difficulty is looked up once per problem from LeetCode's public GraphQL API and
cached in scripts/difficulty_cache.json so later runs are fast.

Standard library only, so it runs on a plain GitHub Actions runner.
"""

import json
import os
import re
import time
import urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(".")
CACHE_PATH = Path("scripts/difficulty_cache.json")
README_PATH = Path("README.md")

# File extension -> language name. Add more here if you ever need them.
LANGS = {
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".py": "Python",
    ".java": "Java",
    ".c": "C",
}
LANG_ORDER = ["C++", "Python", "Java", "C"]
DIFF_ORDER = ["Easy", "Medium", "Hard", "Unsorted"]
SKIP_DIRS = {".git", ".github", "scripts", "node_modules"}
GENERIC_NAMES = {"solution", "main", "index", "answer"}

INTRO = "My LeetCode solutions, synced automatically and sorted by language and difficulty."


def find_solution_files():
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in LANGS:
            yield p


def parse_name(p):
    """Return (problem_number_or_None, slug) guessed from the file/folder name."""
    stem = p.stem
    if stem.lower() in GENERIC_NAMES:
        stem = p.parent.name
    number = None
    m = re.match(r"^(\d+)[\s._-]+", stem)
    if m:
        number = int(m.group(1))
        stem = stem[m.end():]
    slug = re.sub(r"[\s_]+", "-", stem).strip("-").lower()
    return number, slug


def fetch_difficulty(slug):
    """Ask LeetCode for a problem's difficulty. Returns None on any failure."""
    body = json.dumps(
        {
            "query": "query q($s: String!){question(titleSlug:$s){difficulty}}",
            "variables": {"s": slug},
        }
    ).encode()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://leetcode.com/problems/{slug}/",
    }
    session = os.environ.get("LEETCODE_SESSION")
    csrf = os.environ.get("LEETCODE_CSRF_TOKEN")
    if session and csrf:
        headers["Cookie"] = f"LEETCODE_SESSION={session}; csrftoken={csrf}"
        headers["x-csrftoken"] = csrf
    req = urllib.request.Request("https://leetcode.com/graphql", body, headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
        question = (data.get("data") or {}).get("question")
        return question["difficulty"] if question else None
    except Exception as exc:  # network errors, blocked requests, bad JSON
        print(f"Difficulty lookup failed for '{slug}': {exc}")
        return None


def main():
    cache = {}
    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text())
        except json.JSONDecodeError:
            cache = {}

    entries = []
    for p in find_solution_files():
        number, slug = parse_name(p)
        if not slug:
            continue
        if slug not in cache:
            difficulty = fetch_difficulty(slug)
            if difficulty:
                cache[slug] = difficulty
            time.sleep(0.5)  # be polite to the API
        entries.append(
            {
                "lang": LANGS[p.suffix.lower()],
                "diff": cache.get(slug, "Unsorted"),
                "number": number,
                "title": slug.replace("-", " ").title(),
                "path": quote(str(p).replace("\\", "/")),
                "file": p.name,
            }
        )

    # Always write the cache file so the workflow's git add never fails.
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))

    grouped = {}
    for e in entries:
        grouped.setdefault(e["lang"], {}).setdefault(e["diff"], []).append(e)

    lines = ["# LeetCode Solutions", "", INTRO, "", f"**Total solutions: {len(entries)}**", ""]

    langs = sorted(grouped, key=lambda l: LANG_ORDER.index(l) if l in LANG_ORDER else 99)
    for lang in langs:
        lang_total = sum(len(v) for v in grouped[lang].values())
        lines += [f"## {lang} ({lang_total})", ""]
        for diff in DIFF_ORDER:
            items = grouped[lang].get(diff)
            if not items:
                continue
            items.sort(key=lambda e: (e["number"] if e["number"] is not None else 10**9, e["title"]))
            lines += [f"### {diff} ({len(items)})", "", "| # | Problem | Solution |", "|---|---------|----------|"]
            for e in items:
                num = e["number"] if e["number"] is not None else ""
                lines.append(f"| {num} | {e['title']} | [{e['file']}]({e['path']}) |")
            lines.append("")

    README_PATH.write_text("\n".join(lines).rstrip() + "\n")
    print(f"Wrote {README_PATH} with {len(entries)} solutions.")


if __name__ == "__main__":
    main()
