# Setup: leetcode-practice auto-organizer (LeetHub v2)

## What's already done
- [x] GitHub repo created
- [x] `scripts/reorganize.py` and `.github/workflows/organize.yml` pushed to the repo

## Remaining steps

### 1. Install LeetHub v2
Chrome Web Store -> search "LeetHub" by **arunbhardwaj** -> Add to Chrome -> pin it.

### 2. Authorize with GitHub
Click the LeetHub icon -> "Authorize with GitHub" -> approve the popup.

### 3. Connect it to your repo
Click "Get Started" in the popup -> choose your existing **leetcode-practice**
repo (don't let it create a new one). There is **no folder/path setting** in
v2 — it always writes new problem folders straight into the repo root. That's
expected; the GitHub Action handles moving them into place automatically.

### 4. Solve a problem to test it
1. Go to leetcode.com, solve (or resubmit) any Easy problem, get **Accepted**
2. Check your repo after ~15-30 seconds — a new flat folder should appear at
   root, named after the problem
3. Wait another ~30-60 seconds (GitHub Action running) and refresh again —
   that flat folder should be **gone**, replaced by
   `Python/Easy/<Topic>/<problem-name>/` (or `SQL/...`), and the root
   `README.md` should now list it in a table

### 5. If a problem lands in "Uncategorized"
The script asks LeetCode's own API for the official difficulty/topics by
problem slug first (most reliable), and only falls back to reading LeetHub's
generated README.md if that lookup fails. If you see "Uncategorized" for a
problem, it usually means the folder name didn't convert cleanly to a
LeetCode slug — send me the exact folder name LeetHub created and I'll fix
the conversion logic.

## Result structure

```
leetcode-practice/
├── README.md              <- master index, auto-rebuilt every push
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

## How it stays clean automatically
Every time LeetHub v2 drops a new flat folder at root, the Action:
1. Looks up the problem's real difficulty + topics from LeetCode's API
2. **Moves** the folder into `Language/Difficulty/Topic/`
3. Deletes the flat original (so root never gets cluttered)
4. Rebuilds `README.md` and every `<Language>/README.md`
5. Commits and pushes — automatically, in the cloud, no action from you
