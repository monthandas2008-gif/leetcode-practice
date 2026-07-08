# Setup: leetcode-practice auto-organizer

One-time setup, then it runs itself forever.

## 1. Create the GitHub repo

1. Go to github.com/new
2. Name: `leetcode-practice`
3. Public (recruiters/LinkedIn will link here), no README/gitignore needed — leave empty
4. Create repository

## 2. Add these files to the repo

Copy this whole `leetcode-automation` folder's contents into your new repo's root:

```
leetcode-practice/
├── .github/workflows/organize.yml   <- the automation
├── scripts/reorganize.py            <- the reorganizer
└── SETUP.md
```

Commit and push these to `main`.

## 3. Install LeetHub-Neo

1. Chrome Web Store → search "LeetHub-Neo" → Add to Chrome
   (this is the actively maintained fork — the older LeetHub / LeetHub-2.0
   have open sync bugs right now, so use LeetHub-Neo)
2. Click the extension icon → "Authorize with GitHub"
3. Select repository: `leetcode-practice`
4. **Important — set the sync folder to `raw`** (Settings → Repository folder
   setting). This keeps LeetHub-Neo's flat output isolated so the Action can
   reorganize it without fighting your clean structure.
5. In Settings, turn **off** "automatic root README updates" but leave
   "problem and topic syncing" **on** — `reorganize.py` owns the root README now.

## 4. Solve problems as normal

Every time you get an Accepted verdict on LeetCode:
1. LeetHub-Neo pushes the solution + README into `raw/<problem-slug>/`
2. That push triggers the GitHub Action
3. The Action reads difficulty + topics from LeetHub-Neo's README, sorts the
   problem into `Python/Medium/Arrays/...` or `SQL/Easy/Joins/...`, and
   rebuilds the index tables
4. You do nothing. Refresh the repo in ~30 seconds to see it organized.

## 5. First-run check

The very first time this runs, open one of the generated files under
`Python/<Difficulty>/<Topic>/` and confirm the difficulty and topic look
right. LeetHub-Neo's README wording can vary slightly by version — if
`scripts/reorganize.py` mis-parses it (e.g. everything lands in
"Uncategorized"), send me what a real `raw/<problem>/README.md` looks like
and I'll adjust the regex in `parse_metadata()` to match exactly.

## Result structure

```
leetcode-practice/
├── README.md              <- master index, auto-rebuilt
├── raw/                   <- LeetHub-Neo's staging area (ignore this)
├── Python/
│   ├── README.md          <- per-language index
│   ├── Easy/
│   │   ├── Arrays/<problem>/
│   │   └── Hash Table/<problem>/
│   ├── Medium/...
│   └── Hard/...
└── SQL/
    ├── README.md
    ├── Easy/Joins/<problem>/
    └── Medium/...
```
