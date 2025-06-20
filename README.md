<h1 align="center">b3th</h1>
<p align="center">
  <em>AI-powered CLI that stages, commits, pushes, and opens pull-requests for you.</em><br>
  <a href="https://github.com/bethvourc/b3th/actions"><img alt="CI badge" src="https://github.com/bethvourc/b3th/actions/workflows/ci.yml/badge.svg"></a>
</p>

## ✨ Features

| Command          | What it does                                                                                                                                                                    |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `b3th sync`      | **Stage → commit → push** in one shot. b3th asks an LLM for a succinct commit subject + body, then runs `git add --all`, `git commit`, and `git push -u origin &lt;branch&gt;`. |
| `b3th prcreate`  | Pushes the current branch (if needed), summarises commits + diff, and opens a GitHub pull-request, returning the PR URL.                                                        |
| `b3th prdraft`   | Opens a **draft** pull-request (marked “Draft” on GitHub) after generating the title/body with the LLM.                                                                         |
| `b3th stats`     | Shows commit count, unique files touched, and line additions/deletions for a given time-frame (e.g. `--last 7d`).                                                               |
| `b3th summarize` | Uses an LLM to produce a one-paragraph summary of the last _N_ commits (default 10).                                                                                            |

_(The legacy `b3th commit` still works but prints a deprecation warning and delegates to **sync**.)_

Under the hood, b3th leverages **Groq’s Chat Completions API** for language
generation and the **GitHub REST API** for PR creation.

---

## 🚀 Quick Install

### 1 · Prerequisites

- **Python ≥ 3.9**
- **Git** in your `PATH`.
- **Poetry** (preferred) or plain `pip`.  
  <sub>Install Poetry &rarr; `curl -sSL https://install.python-poetry.org | python3 -`</sub>

### 2 · Install the package

<details>
<summary><strong>Option A – From PyPI</strong> (when published)</summary>

```bash
pipx install b3th         # keeps deps isolated
# or
pip install --user b3th
```

</details>

<details>
<summary><strong>Option B – From source</strong> (recommended for contributors)</summary>

```bash
git clone https://github.com/bethvourc/b3th.git
cd b3th
poetry install
```

</details>

### 3 · Set up your secrets

Create a `.env` in the project root **or** export env-vars in your shell:

```dotenv
GROQ_API_KEY="sk_live_xxx"        # Get one → https://console.groq.com/keys
GITHUB_TOKEN="ghp_xxx"            # PAT with repo scope → https://github.com/settings/tokens
# Optional
# GROQ_MODEL_ID="llama-3.3-70b-versatile"
```

> **Tip** b3th auto-loads `.env` at runtime via `python-dotenv`.

### 4 · (Dev only) Install Git hooks

```bash
poetry run pre-commit install   # auto-format & lint on each commit
```

---

## 🕹️ CLI Usage

```bash
# One-shot stage → commit → push
poetry run b3th sync                   # interactive
poetry run b3th sync -y                # non-interactive

# Create a pull-request into 'main'
poetry run b3th prcreate               # interactive
poetry run b3th prcreate -b develop -y # specify base branch, skip confirm

# Create a draft pull-request to 'main'
poetry run b3th prdraft               # interactive confirm
poetry run b3th prdraft -b develop -y # specify base branch, skip confirm

# Git statistics (last 7 days)
poetry run b3th stats --last 7d

# Summarise last 15 commits
poetry run b3th summarize -n 15
```

### Sync Demo

```text
$ b3th sync
Proposed commit message:
feat(utils): support .env loading

Load environment variables automatically from a .env file using python-dotenv
so users don't need to export them manually each session.

Proceed with commit & push? [y/N]: y
🚀 Synced! Commit pushed to origin.
```

### Stats Demo

```bash
$ b3th stats --last 7d
Commits:    14
Files:      6
Additions:  +120
Deletions:  -34
```

### Summarize Demo

```bash
$ b3th summarize -n 10
Introduce a comprehensive stats command, improve README instructions,
and fix a minor UI colour bug—enhancing insight, onboarding, and UX.
```

---

## 🛠️ Contributing

1. Fork & clone.
2. `poetry install && pre-commit install`
3. Create a branch: `git switch -c feat/your-idea`
4. Run `pytest` before pushing.
5. Open a PR—b3th’s CI enforces **≥ 85 %** coverage 🛡️

---

## 📜 License

Licensed under the **MIT License** – see `LICENSE` for details.

Commit:

```bash
git add README.md
git commit -m "docs: add stats & summarize commands to README"
```
