# Quick Start Guide - GitHub Setup

10-minute setup to get your AViD Journal repository on GitHub.

---

## Step 1: Create Local Repository (2 min)

```bash
# Create project directory
mkdir avid-journal
cd avid-journal

# Initialize git
git init
git branch -M main

# Download all files from Claude
# (You should have these files ready)
```

---

## Step 2: Organize Files (3 min)

Copy your existing code into this structure:

```
avid-journal/
├── src/
│   ├── parser/
│   │   ├── latex_parser.py      ← YOUR EXISTING FILE
│   │   └── parse_tex.py         ← YOUR EXISTING FILE
│   │
│   ├── novelty/
│   │   └── (empty for now)
│   │
│   ├── formalization/
│   │   ├── lean_project.py      ← YOUR EXISTING FILE
│   │   ├── numina_interface.py  ← YOUR EXISTING FILE
│   │   └── orchestrator.py      ← YOUR EXISTING FILE
│   │
│   └── database/
│       └── db.py                ← YOUR EXISTING FILE
│
├── tests/
│   └── (empty for now)
│
├── docs/
│   ├── ARCHITECTURE.md          ← FROM CLAUDE
│   └── PROGRESS.md              ← FROM CLAUDE
│
├── .gitignore                   ← FROM CLAUDE
├── requirements.txt             ← FROM CLAUDE
├── LICENSE                      ← FROM CLAUDE
├── setup.sh                     ← FROM CLAUDE
└── README.md                    ← FROM CLAUDE
```

---

## Step 3: Create GitHub Repository (2 min)

1. Go to https://github.com/new

2. Fill in:
   - **Repository name:** `avid-journal`
   - **Description:** "Automated mathematics journal with Lean 4 verification"
   - **Visibility:** Private ✓
   - **DO NOT** initialize with README, .gitignore, or license (we have them)

3. Click "Create repository"

---

## Step 4: Push to GitHub (2 min)

```bash
# Add all files
git add .

# Commit
git commit -m "Initial commit - AViD Journal codebase"

# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/avid-journal.git

# Push
git push -u origin main
```

**Done! Your repository is live.**

---

## Step 5: Verify (1 min)

Go to: `https://github.com/YOUR_USERNAME/avid-journal`

You should see:
- ✓ README with project description
- ✓ Source code in `src/`
- ✓ Documentation in `docs/`
- ✓ MIT License

---

## What to Do Next

### For Future Conversations with Claude:

Just send:
```
Repo: https://github.com/YOUR_USERNAME/avid-journal
Working on: src/novelty/arxiv_search.py
Context: Implementing ArXiv paper search with Semantic Scholar API
```

Claude will be able to see your whole codebase and help accordingly.

---

### Update Progress

After each work session:

```bash
# Add changes
git add .

# Commit with descriptive message
git commit -m "Add ArXiv search module with Semantic Scholar API"

# Push
git push
```

---

### Clone on Another Machine

```bash
git clone https://github.com/YOUR_USERNAME/avid-journal.git
cd avid-journal
bash setup.sh
```

---

## Troubleshooting

### "Permission denied (publickey)"

**Solution:** Setup SSH key or use HTTPS with personal access token.

```bash
# Use HTTPS instead
git remote set-url origin https://github.com/YOUR_USERNAME/avid-journal.git
```

### "Repository not found"

**Solution:** Check repository name and visibility. Make sure you created it.

### "Git not installed"

**Solution:** Install git:
- **Windows:** https://git-scm.com/download/win
- **Mac:** `brew install git`
- **Linux:** `sudo apt install git`

---

## Tips

1. **Commit often** - After each feature, commit
2. **Descriptive messages** - "Add X" not "update"
3. **Push regularly** - Backup + easier to share
4. **Branch for experiments** - `git checkout -b experiment-xyz`

---

## Ready!

You now have:
- ✅ Professional repo structure
- ✅ Version control
- ✅ Backup on GitHub
- ✅ Easy to share with Claude
- ✅ Ready for PhD applications

**Next:** Start working on `src/novelty/arxiv_search.py` 🚀
