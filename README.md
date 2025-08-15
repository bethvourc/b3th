<h1 align="center">b3th</h1>
<p align="center">
  <em>AI-powered CLI that stages, commits, pushes, proposes merge resolutions, and opens pull-requests for you.</em><br>
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
| `b3th resolve`   | Scans for Git **merge conflicts**, builds a per-file prompt, asks the LLM for a merged version, writes `<file>.resolved`; `--apply` overwrites originals with the suggestions.  |

_(The legacy `b3th commit` still works but prints a deprecation warning and delegates to **sync**.)_

Under the hood, b3th leverages **Groq’s Chat Completions API** for language generation and the **GitHub REST API** for PR creation.

---

## Quick Install

### 1 · Prerequisites

- **Python ≥ 3.9**
- **Git** in your `PATH`.
- **Poetry** (preferred) or plain `pip`. <sub>Install Poetry → `curl -sSL https://install.python-poetry.org | python3 -`</sub>

### 2 · Install the package

<details>
<summary><strong>Option A – From PyPI</strong> (when published)</summary>

```bash
pipx install b3th         # keeps deps isolated
# or
pip install --user b3th
```

> **Important:** Installing the package is not enough.  
> You still must provide credentials (see **“Set up your secrets”** below) via:
>
> - exported environment variables, or
> - a **project-level `.env`** file, or
> - a **TOML config file** (see examples below).

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

You can provide credentials in **either** your shell environment, a **project `.env`**, or a **TOML config** file.

#### A) Environment variables or project `.env` (simplest)

Put this in your environment (e.g. `export` in shell init) **or** in a **project-level `.env`**:

```dotenv
# <repo>/.env   (project-level)
GROQ_API_KEY="sk_live_xxx"        # https://console.groq.com/keys
GITHUB_TOKEN="ghp_xxx"            # PAT with repo scope → https://github.com/settings/tokens
# Optional
# GROQ_MODEL_ID="llama-3.3-70b-versatile"
```

> **How `.env` loading works**
>
> b3th auto-loads **the nearest `.env` in your project tree** (using `python-dotenv`’s `find_dotenv(usecwd=True)`).  
> It does **not** automatically read `~/.env`. If you prefer user-level credentials, either export them in your shell or use the TOML option below.

#### B) TOML config file (good for user-level/global setup)

Create:

```
~/.config/b3th/config.toml
```

On macOS/Linux with XDG:

```
$XDG_CONFIG_HOME/b3th/config.toml
```

Or point to a custom file via:

```
B3TH_CONFIG=/path/to/config.toml
```

Example contents:

```toml
[github]
token = "ghp_xxx"

[groq]
api_key = "sk_live_xxx"
```

> **Precedence:** environment variables (including values loaded from the project `.env`) take priority over TOML.

> **Security tip:** Add `.env` to your `.gitignore` and avoid committing secrets.

### 4 · (Dev only) Install Git hooks

```bash
poetry run pre-commit install   # auto-format & lint on each commit
```

---

## CLI Usage

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

# Generate conflict suggestions (writes *.resolved files)
poetry run b3th resolve

# Accept suggestions and overwrite originals
poetry run b3th resolve --apply
```

### Sync Demo

```text
$ b3th sync
Proposed commit message:
feat(utils): support .env loading

Load environment variables automatically from the nearest project .env
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

### Resolve Demo

```bash
# Create .resolved files next to conflicted originals
$ b3th resolve
🔍 Detecting conflicts & asking the LLM…
💡 Generated 2 *.resolved file(s).
Inspect the *.resolved files. Run again with --apply to accept.

# Overwrite originals with merged suggestions
$ b3th resolve --apply
✅ Originals overwritten with LLM suggestions.
```

### Conflict-Resolver Workflow

1. **Run** `b3th resolve` to generate `<file>.resolved` for each conflicted file.
2. **Review** the proposed merges; tweak if needed.
3. **Apply** with `b3th resolve --apply` to overwrite originals and remove the `.resolved` files.
4. **Commit** your merged changes.

---

## Releasing (GitHub Actions + Trusted Publisher)

1. `poetry version patch` (or `minor`/`major`) and commit.
2. Tag: `git tag -a v$(poetry version -s) -m "b3th v$(poetry version -s)" && git push origin v$(poetry version -s)`
3. The workflow builds and uploads to PyPI automatically.

---

## Contributing

1. Fork & clone.
2. `poetry install && pre-commit install`
3. Create a branch: `git switch -c feat/your-idea`
4. Run `pytest` before pushing.
5. Open a PR—b3th’s CI enforces **≥ 85 %** coverage.

---

## License

Licensed under the **MIT License** – see `LICENSE` for details.
