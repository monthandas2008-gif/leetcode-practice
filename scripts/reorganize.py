#!/usr/bin/env python3
"""
Reorganizes LeetHub-Neo's flat sync output (raw/<problem-slug>/...) into:

    <Language>/<Difficulty>/<Topic>/<problem-slug>/
        README.md
        <solution file>

Also rebuilds:
    README.md                  -> master index (table of every problem)
    <Language>/README.md       -> per-language index

Run automatically by .github/workflows/organize.yml on every push to raw/.
Safe to re-run: it fully rebuilds organized/ each time from raw/, so it
never drifts or duplicates.
"""

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
ORG_DIR = ROOT

# Map file extensions LeetHub-Neo produces -> your top-level language folders.
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


def detect_language(problem_dir: Path) -> str | None:
    for f in problem_dir.iterdir():
        if f.name in SKIP_FILES or f.is_dir():
            continue
        if f.suffix in LANG_MAP:
            return LANG_MAP[f.suffix]
    return None


def parse_metadata(readme_text: str) -> tuple[str, list[str]]:
    """Extract difficulty and topic list from a LeetHub-Neo README.md.

    Tries a few common formats since exact wording can vary by version:
      **Difficulty:** Medium
      Difficulty: Medium
      Topics: Array, Hash Table
      Tags: Array, Hash Table
    """
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


def clean_generated_dirs():
    """Remove previously generated language folders so we rebuild fresh."""
    for name in LANG_MAP.values():
        d = ORG_DIR / name
        if d.exists():
            shutil.rmtree(d)


def main():
    if not RAW_DIR.exists():
        print(f"No raw/ folder found at {RAW_DIR} — nothing to organize yet.")
        return

    clean_generated_dirs()
    index_rows = []  # (language, difficulty, topic, name, path)

    for problem_dir in sorted(RAW_DIR.iterdir()):
        if not problem_dir.is_dir():
            continue

        readme_path = problem_dir / "README.md"
        readme_text = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

        language = detect_language(problem_dir)
        if language is None:
            print(f"  ! Skipping '{problem_dir.name}': no recognized solution file.")
            continue

        difficulty, topics = parse_metadata(readme_text)
        primary_topic = topics[0]  # file lives under its primary topic

        dest = ORG_DIR / language / difficulty / primary_topic / problem_dir.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(problem_dir, dest, dirs_exist_ok=True)

        rel_path = dest.relative_to(ORG_DIR)
        index_rows.append((language, difficulty, ", ".join(topics), problem_dir.name, str(rel_path)))
        print(f"  -> {problem_dir.name}: {language} / {difficulty} / {primary_topic}")

    write_master_index(index_rows)
    write_language_indexes(index_rows)


def write_master_index(rows):
    diff_order = {"Easy": 0, "Medium": 1, "Hard": 2, "Uncategorized": 3}
    rows_sorted = sorted(rows, key=lambda r: (r[0], diff_order.get(r[1], 9), r[2], r[3]))

    lines = [
        "# LeetCode Practice\n",
        "Auto-generated index. Do not edit by hand — this file is rebuilt by ",
        "`scripts/reorganize.py` on every push. Solutions land here automatically ",
        "via LeetHub-Neo -> `raw/` -> GitHub Action.\n",
        f"**Total problems:** {len(rows_sorted)}\n",
        "| Problem | Language | Difficulty | Topics | Path |",
        "|---|---|---|---|---|",
    ]
    for lang, diff, topics, name, path in rows_sorted:
        lines.append(f"| {name} | {lang} | {diff} | {topics} | [{path}]({path}) |")

    (ORG_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_language_indexes(rows):
    by_lang: dict[str, list] = {}
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
