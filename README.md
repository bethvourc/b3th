<h1 align="center">b3th</h1>
<p align="center">
  <em>AI-powered CLI that stages, commits, pushes, and opens pull-requests for you.</em><br>
  <a href="https://github.com/bethvourc/b3th/actions"></a>
</p>

---

## ✨ Features

| Command         | What it does                                                                                                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `b3th sync`     | **Stage → commit → push** in one shot. b3th asks an LLM for a succinct commit subject + body, then runs `git add --all`, `git commit`, and `git push -u origin &lt;branch&gt;`. |
| `b3th prcreate` | Pushes the current branch (if needed), summarizes commits + diff, and opens a GitHub pull-request, returning the PR URL.                                                        |

_(The legacy `b3th commit` still works but prints a deprecation warning and delegates to **sync**.)_

Under the hood, b3th uses **Groq’s Chat Completions API** for language
generation and the **GitHub REST API** for PR creation.

---

## 🚀 Quick Install

### 1 · Prerequisites

- **Python ≥ 3.9**
- **Git** installed and in your `PATH`.
- **Poetry** (preferred) or plain `pip`.  
  <sub>Install Poetry → `curl -sSL https://install.python-poetry.org | python3 -`</sub>

### 2 · Install the package

<details>
<summary>Option A – From PyPI (when published)</summary>

```bash
pipx install b3th           # keeps dependencies isolated
# or
pip install --user b3th
```

</details>

<details>
<summary>Option B – From source (recommended for contributors)</summary>

```bash
git clone https://github.com/bethvourc/b3th.git
cd b3th
poetry install
```

</details>

### 3 · Set up your secrets

Create a `.env` file in the project root **or** export vars in your shell:

```dotenv
# .env
GROQ_API_KEY="sk_live_xxx"          # get one at https://console.groq.com/keys
GITHUB_TOKEN="ghp_xxx"              # PAT with repo scope (https://github.com/settings/tokens)
# Optional overrides
# GROQ_MODEL_ID="llama-3.3-70b-versatile"
```

> **Tip**: b3th automatically loads `.env` at runtime via `python-dotenv`.

### 4 · (Dev only) Install Git hooks

```bash
poetry run pre-commit install   # formats & lints on every commit
```

---

## 🕹️ CLI Usage

```bash
# One-shot stage → commit → push
poetry run b3th sync                  # interactive confirm
poetry run b3th sync -y               # non-interactive

# Create a pull-request to 'main' from your current branch
poetry run b3th prcreate              # interactive confirm
poetry run b3th prcreate -b develop -y   # specify base branch, skip confirm
```

### Demo

```text
$ b3th sync
Proposed commit message:
feat(utils): support .env loading

Load environment variables automatically from a .env file using python-dotenv
so users don't need to export them manually each session.

Proceed with commit & push? [y/N]: y
🚀 Synced! Commit pushed to origin.
```

---

## 🛠️ Contributing

1. Fork & clone.
2. `poetry install && pre-commit install`.
3. Create a feature branch: `git switch -c feat/your-idea`.
4. Run `pytest` before pushing.
5. Open a PR — b3th’s CI enforces ≥ 85 % coverage 🛡️.

---

## 📜 License

This project is licensed under the MIT License – see `LICENSE` for details.

Commit the change:

```bash
git add README.md
git commit -m "docs: update README for b3th sync command"
```
