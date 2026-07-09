#!/usr/bin/env python3
"""
Reorganizes LeetHub v2's synced output into:

    <Language>/<Difficulty>/<Topic>/<problem-slug>/
        README.md
        <solution file>

Also rebuilds:
    README.md                  -> master index (table of every problem)
    <Language>/README.md       -> per-language index

LeetHub v2 has NO configurable sync path -- it always drops one folder per
solved problem straight into the repo ROOT. So this script scans the repo
root for "problem-looking" folders (anything not in MANAGED_NAMES), figures
out each one's difficulty/topic, MOVES it into the organized structure, and
removes the flat original -- so the root stays clean instead of showing both
a flat copy and an organized copy.

Difficulty and topics are fetched from LeetCode's public GraphQL API by
problem slug (reliable regardless of which extension/version wrote the
folder). If that lookup fails (offline, rate limited, unrecognized slug),
it falls back to parsing the problem's own README.md.

Run automatically by .github/workflows/organize.yml on every push.
Safe to re-run: already-organized folders live under LANG_MAP names, which
are excluded from re-scanning, so nothing is ever processed twice.
"""

import json
import re
import shutil
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORG_DIR = ROOT

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

# Map file extensions LeetHub v2 produces -> your top-level language folders.
# Add to this as you solve problems in more languages.
LANG_MAP = {
    ".py": "Python",
    ".sql": "SQL",
    ".java": "Java",
    ".cpp": "Cpp",
    ".c": "C",
    ".js": "JavaScript",
    ".ts": "TypeScript",
}

VALID_DIFFICULTIES = {"Easy", "Medium", "Hard"}
SKIP_FILES = {"README.md", "NOTES.md", "notes.md"}

# Everything at repo root that is OUR scaffolding, not an incoming LeetHub
# problem folder. Includes our own generated language folders so re-runs
# never try to "organize" already-organized output.
MANAGED_NAMES = {
    ".git", ".github", ".gitignore", "scripts", "README.md", "SETUP.md",
    "LICENSE", "raw",
    *LANG_MAP.values(),
}


def detect_language(problem_dir: Path):
    for f in problem_dir.iterdir():
        if f.is_dir() or f.name in SKIP_FILES:
            continue
        if f.suffix in LANG_MAP:
            return LANG_MAP[f.suffix]
    return None


def slug_from_folder_name(folder_name: str) -> str:
    """Turn a LeetHub-style folder name into a LeetCode titleSlug.

    Handles common naming conventions:
      "1-two-sum"     -> "two-sum"
      "two-sum"       -> "two-sum"
      "0001-two-sum"  -> "two-sum"
    """
    return re.sub(r"^\d+[\-\.\s]*", "", folder_name).strip().lower()


def fetch_metadata_from_leetcode(slug: str):
    """Query LeetCode's public GraphQL API for a problem's difficulty/topics.
    Returns None on any failure so the caller falls back to README parsing.
    """
    query = {
        "operationName": "questionData",
        "variables": {"titleSlug": slug},
        "query": """
            query questionData($titleSlug: String!) {
                question(titleSlug: $titleSlug) {
                    difficulty
                    topicTags { name }
                }
            }
        """,
    }
    req = urllib.request.Request(
        LEETCODE_GRAPHQL_URL,
        data=json.dumps(query).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (leetcode-practice-organizer)",
            "Referer": f"https://leetcode.com/problems/{slug}/",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        q = data.get("data", {}).get("question")
        if not q:
            return None
        difficulty = q.get("difficulty") or "Uncategorized"
        topics = [t["name"] for t in q.get("topicTags", [])] or ["General"]
        return difficulty, topics
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError, KeyError, ValueError):
        return None


def parse_metadata_from_readme(readme_text: str):
    """Fallback: extract difficulty/topics from the problem's own README.md."""
    diff_match = re.search(r"Difficulty[:\*\s]+\**\s*(Easy|Medium|Hard)", readme_text, re.I)
    difficulty = diff_match.group(1).capitalize() if diff_match else "Uncategorized"
    if difficulty not in VALID_DIFFICULTIES:
        difficulty = "Uncategorized"

    topics_match = re.search(r"(?:Topics|Tags)[:\*\s]+([^\n]+)", readme_text, re.I)
    if topics_match:
        raw = topics_match.group(1)
        topics = [t.strip(" *`[]()") for t in re.split(r"[,#]", raw) if t.strip(" *`[]()")]
    else:
        topics = []
    return difficulty, (topics or ["General"])


def get_metadata(problem_dir: Path, readme_text: str):
    """Try LeetCode's API first (reliable across extensions), then README."""
    slug = slug_from_folder_name(problem_dir.name)
    api_result = fetch_metadata_from_leetcode(slug)
    if api_result is not None:
        return api_result
    print(f"  (API lookup failed for '{slug}', falling back to README parsing)")
    return parse_metadata_from_readme(readme_text)


def find_problem_dirs():
    """Find candidate problem folders. Checks raw/ first (LeetHub-Neo style)
    then falls back to scanning repo root (LeetHub v2 style)."""
    raw_dir = ROOT / "raw"
    if raw_dir.exists() and any(raw_dir.iterdir()):
        return list(raw_dir.iterdir()), True  # (dirs, came_from_raw)

    candidates = [
        p for p in ROOT.iterdir()
        if p.is_dir() and p.name not in MANAGED_NAMES and not p.name.startswith(".")
    ]
    return candidates, False


def main():
    problem_dirs, from_raw = find_problem_dirs()
    if not problem_dirs:
        print("No new problem folders found to organize.")
        return

    index_rows = []  # (language, difficulty, topic, name, path)

    for problem_dir in sorted(problem_dirs):
        if not problem_dir.is_dir():
            continue

        readme_path = problem_dir / "README.md"
        readme_text = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

        language = detect_language(problem_dir)
        if language is None:
            print(f"  ! Skipping '{problem_dir.name}': no recognized solution file.")
            continue

        difficulty, topics = get_metadata(problem_dir, readme_text)
        primary_topic = topics[0]

        dest = ORG_DIR / language / difficulty / primary_topic / problem_dir.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(problem_dir), str(dest))

        rel_path = dest.relative_to(ORG_DIR)
        index_rows.append((language, difficulty, ", ".join(topics), problem_dir.name, str(rel_path)))
        print(f"  -> {problem_dir.name}: {language} / {difficulty} / {primary_topic}")

    rebuild_indexes_from_existing_structure()


def collect_existing_rows():
    """Walk the already-organized folders so indexes always reflect
    everything, not just what moved in this run."""
    rows = []
    for lang in LANG_MAP.values():
        lang_dir = ORG_DIR / lang
        if not lang_dir.exists():
            continue
        for diff_dir in lang_dir.iterdir():
            if not diff_dir.is_dir():
                continue
            for topic_dir in diff_dir.iterdir():
                if not topic_dir.is_dir():
                    continue
                for problem_dir in topic_dir.iterdir():
                    if not problem_dir.is_dir():
                        continue
                    rel_path = problem_dir.relative_to(ORG_DIR)
                    rows.append((lang, diff_dir.name, topic_dir.name, problem_dir.name, str(rel_path)))
    return rows


def rebuild_indexes_from_existing_structure():
    rows = collect_existing_rows()
    write_master_index(rows)
    write_language_indexes(rows)


def write_master_index(rows):
    diff_order = {"Easy": 0, "Medium": 1, "Hard": 2, "Uncategorized": 3}
    rows_sorted = sorted(rows, key=lambda r: (r[0], diff_order.get(r[1], 9), r[2], r[3]))

    lines = [
        "# LeetCode Practice\n",
        "Auto-generated index. Do not edit by hand -- this file is rebuilt by "
        "`scripts/reorganize.py` on every push. Solutions land here automatically "
        "via LeetHub v2 -> GitHub Action.\n",
        f"**Total problems:** {len(rows_sorted)}\n",
        "| Problem | Language | Difficulty | Topics | Path |",
        "|---|---|---|---|---|",
    ]
    for lang, diff, topics, name, path in rows_sorted:
        lines.append(f"| {name} | {lang} | {diff} | {topics} | [{path}]({path}) |")

    (ORG_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_language_indexes(rows):
    by_lang = {}
    for row in rows:
        by_lang.setdefault(row[0], []).append(row)

    diff_order = {"Easy": 0, "Medium": 1, "Hard": 2, "Uncategorized": 3}
    for lang, lang_rows in by_lang.items():
        lang_rows.sort(key=lambda r: (diff_order.get(r[1], 9), r[2], r[3]))
        lines = [f"# {lang} Solutions\n", "| Problem | Difficulty | Topics | Path |", "|---|---|---|---|"]
        for _, diff, topics, name, path in lang_rows:
            rel = Path(path).relative_to(lang)
            lines.append(f"| {name} | {diff} | {topics} | [{rel}]({rel}) |")
        (ORG_DIR / lang / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
