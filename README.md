# agentplugins

Public, lightweight plugins for **Cursor**, **Claude Code**, and **Codex**.

Repo: [github.com/gmanova/agentplugins](https://github.com/gmanova/agentplugins)

## Plugins

| Plugin | What it does |
|---|---|
| [`etoro-context-tracker`](plugins/etoro-context-tracker/) | One-line context footer every reply; writes a handoff file when the thread goes red. Cursor self-estimates (`~`); Claude/Codex report exact usage. |

## Install (any OS)

Needs **Python 3** on `PATH`.

```bash
git clone https://github.com/gmanova/agentplugins.git
cd agentplugins/plugins/etoro-context-tracker

# Canonical (macOS / Linux / Windows)
python3 scripts/install.py --target all

# Wrappers
./scripts/install.sh --target all          # macOS / Linux
.\scripts\install.ps1 -Target All          # Windows PowerShell
```

Targets: `cursor` | `claude` | `codex` | `all`

### Claude Code only (marketplace)

```bash
claude plugin marketplace add https://github.com/gmanova/agentplugins.git
# or after clone:
claude plugin marketplace add /path/to/agentplugins

claude plugin install etoro-context-tracker@agentplugins
```

### Cursor only (manual)

```bash
# after clone
cp -R plugins/etoro-context-tracker ~/.cursor/plugins/local/etoro-context-tracker
# Windows: Copy-Item -Recurse ...
```

Then **Developer: Reload Window** → new chat → you should see a one-line footer:
`⚡ Turn 1 | ~…K chat / ~…K total | 🟢`

## Layout

```
.claude-plugin/marketplace.json   Claude marketplace manifest
plugins/
  etoro-context-tracker/          first plugin
```

## License

MIT — see [LICENSE](LICENSE).
