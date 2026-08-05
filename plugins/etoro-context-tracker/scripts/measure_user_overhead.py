#!/usr/bin/env python3
"""Measure user-controlled context overhead (not platform tools).

Counts:
  - alwaysApply: true rule bodies (workspace + ~/.cursor/rules + plugin rules)
  - Skill description YAML only (same roots agents typically scan)
  - MCP server name stubs from common MCP config files (cheap)

Excludes built-in tool schemas, IDE scaffolding, and chat growth.

Stdout: JSON. Cache: $TEMP/etoro-context-overhead.json (1 hour reuse).
Always exits 0. Stdlib only.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

CACHE_TTL_SEC = 3600
CACHE_NAME = "etoro-context-overhead.json"
TOP_N = 15

# Optional override for CI / forced refresh
FORCE = "--force" in sys.argv or os.environ.get("ETORO_OVERHEAD_FORCE") == "1"


def _home() -> Path:
    return Path.home()


def _temp_cache() -> Path:
    base = os.environ.get("TEMP") or os.environ.get("TMPDIR") or os.environ.get("TMP") or "/tmp"
    return Path(base) / CACHE_NAME


def _tok(chars: int) -> float:
    return round(chars / 4 / 1000, 3)


def _workspace_roots() -> list[Path]:
    roots: list[Path] = []
    for key in ("CURSOR_PROJECT_DIR", "CLAUDE_PROJECT_DIR", "PWD"):
        v = os.environ.get(key)
        if v:
            p = Path(v)
            if p.is_dir():
                roots.append(p)
    # Walk up from cwd looking for .cursor / .git
    cwd = Path.cwd()
    for p in [cwd, *cwd.parents]:
        if (p / ".cursor").is_dir() or (p / ".git").is_dir():
            roots.append(p)
            break
        if p == p.parent:
            break
    # Dedupe
    out: list[Path] = []
    seen: set[str] = set()
    for r in roots:
        key = str(r.resolve()).lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return {}
    fm = m.group(1)
    fields: dict[str, str] = {}
    # alwaysApply
    am = re.search(r"^alwaysApply:\s*(true|false)\s*$", fm, re.M | re.I)
    if am:
        fields["alwaysApply"] = am.group(1).lower()
    # name
    nm = re.search(r"^name:\s*(.+)$", fm, re.M)
    if nm:
        fields["name"] = nm.group(1).strip().strip("\"'")
    # description — quoted, block, or plain
    dm = re.search(r"^description:\s*(.*)", fm, re.M)
    if dm:
        rest = dm.group(1).strip()
        if rest.startswith('"') or rest.startswith("'"):
            q = rest[0]
            # single-line quoted (may be long)
            line = rest
            # find closing quote on same line (handle escapes loosely)
            if line.endswith(q) and len(line) > 1:
                fields["description"] = line[1:-1]
            else:
                fields["description"] = line.strip("\"'")
        elif rest in (">", ">-", "|", "|-"):
            lines = []
            after = fm[dm.end() :]
            for line in after.splitlines():
                if re.match(r"^[a-zA-Z0-9_]+:", line):
                    break
                if line.startswith(" ") or line.startswith("\t") or line.strip() == "":
                    lines.append(line.strip())
                else:
                    break
            fields["description"] = " ".join(x for x in lines if x)
        else:
            fields["description"] = rest
    return fields


def _skill_desc_chars(skill_md: Path) -> tuple[str, int]:
    try:
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return skill_md.parent.name, 0
    fields = _parse_frontmatter(text)
    name = fields.get("name") or skill_md.parent.name
    desc = fields.get("description") or ""
    payload = f"{name}: {desc}"
    return name, len(payload)


def _host_is_cursor() -> bool:
    """True when this measure run is for a Cursor session (skip Claude-only plugin caches)."""
    if os.environ.get("CURSOR_PROJECT_DIR") or os.environ.get("CURSOR_AGENT"):
        return True
    # Script installed under ~/.cursor/plugins → Cursor copy
    try:
        return "cursor" in Path(__file__).resolve().parts
    except NameError:
        return False


def _is_quarantined(path: Path) -> bool:
    """Skip figma-style quarantine dirs (rules._disabled / skills._disabled) and junk."""
    key = str(path).lower()
    if any(x in key for x in ("_skill-archive", "node_modules", "backup_")):
        return True
    for part in path.parts:
        pl = part.lower()
        if pl.endswith("._disabled") or pl.endswith(".disabled"):
            return True
    return False


def _rule_body_chars(path: Path) -> tuple[bool, int]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False, 0
    fields = _parse_frontmatter(text)
    if fields.get("alwaysApply") != "true":
        # AGENTS.md / CLAUDE.md at workspace/user root — always-on if no frontmatter.
        # Do NOT count plugin copies (Codex AGENTS.md etc.) — they are not Cursor alwaysApply.
        if path.name.upper() in ("AGENTS.MD", "CLAUDE.MD") and not fields:
            if "plugins" in path.parts:
                return False, 0
            return True, len(text)
        return False, 0
    return True, len(text)


def _dedupe_by_name(items: list[dict]) -> list[dict]:
    """Keep first occurrence of each basename (callers pass priority-ordered lists)."""
    out: list[dict] = []
    seen: set[str] = set()
    for it in items:
        name = (it.get("name") or "").lower()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(it)
    return out


def _collect_rules(workspaces: list[Path]) -> list[dict]:
    # Priority order: workspace → user rules → Cursor local plugins → Cursor cache.
    # Claude plugin cache is skipped when measuring for Cursor (cross-agent phantom).
    candidates: list[Path] = []
    for ws in workspaces:
        candidates.append(ws / ".cursor" / "rules")
        candidates.append(ws / "AGENTS.md")
        candidates.append(ws / "CLAUDE.md")
    candidates.append(_home() / ".cursor" / "rules")
    plugin_bases = [
        _home() / ".cursor" / "plugins" / "local",
        _home() / ".cursor" / "plugins" / "cache",
    ]
    if not _host_is_cursor():
        plugin_bases.append(_home() / ".claude" / "plugins" / "cache")
    for base in plugin_bases:
        if base.is_dir():
            candidates.append(base)

    path_seen: set[str] = set()
    raw: list[dict] = []
    for c in candidates:
        files: list[Path] = []
        if c.is_file() and c.suffix.lower() in (".md", ".mdc"):
            files.append(c)
        elif c.is_dir():
            for p in c.rglob("*.mdc"):
                files.append(p)
            for p in c.rglob("*.md"):
                if "rules" in p.parts or p.name.upper() in ("AGENTS.MD", "CLAUDE.MD"):
                    files.append(p)
        for p in files:
            key = str(p.resolve()).lower()
            if key in path_seen or _is_quarantined(p):
                continue
            path_seen.add(key)
            always, chars = _rule_body_chars(p)
            if not always or chars <= 0:
                continue
            raw.append(
                {
                    "kind": "rule",
                    "path": str(p),
                    "name": p.name,
                    "chars": chars,
                    "tok_k": _tok(chars),
                }
            )
    # Dedupe identical rule filenames across marketplace/product-team caches
    return _dedupe_by_name(raw)


def _collect_skills(workspaces: list[Path]) -> list[dict]:
    # Priority: workspace → Cursor user skills → Claude → Codex → plugin caches (Cursor only when host=Cursor)
    roots: list[Path] = []
    for ws in workspaces:
        roots.append(ws / ".cursor" / "skills")
        roots.append(ws / ".claude" / "skills")
    roots.extend(
        [
            _home() / ".cursor" / "skills",
            _home() / ".cursor" / "skills-cursor",
            _home() / ".claude" / "skills",
            _home() / ".codex" / "skills",
        ]
    )
    plugin_bases = [
        _home() / ".cursor" / "plugins" / "local",
        _home() / ".cursor" / "plugins" / "cache",
    ]
    if not _host_is_cursor():
        plugin_bases.append(_home() / ".claude" / "plugins" / "cache")
    for base in plugin_bases:
        if base.is_dir():
            roots.append(base)

    path_seen: set[str] = set()
    raw: list[dict] = []
    for root in roots:
        if not root.is_dir():
            continue
        for sm in root.rglob("SKILL.md"):
            key = str(sm.resolve()).lower()
            if key in path_seen or _is_quarantined(sm):
                continue
            # Prefer .../skills/<name>/SKILL.md (skip skills._disabled via quarantine)
            if "skills" not in sm.parts:
                continue
            path_seen.add(key)
            name, chars = _skill_desc_chars(sm)
            if chars <= 0:
                continue
            raw.append(
                {
                    "kind": "skill",
                    "path": str(sm),
                    "name": name,
                    "chars": chars,
                    "tok_k": _tok(chars),
                }
            )
    # One entry per skill name (first = highest priority root)
    return _dedupe_by_name(raw)


def _collect_mcp() -> list[dict]:
    """Cheap stub: ~80 tokens per configured server name."""
    # Prefer host-local MCP config; avoid double-counting Claude+Codex when on Cursor.
    if _host_is_cursor():
        configs: list[Path] = [
            _home() / ".cursor" / "mcp.json",
            _home() / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage" / "cursor.mcp" / "mcp.json",
        ]
    else:
        configs = [
            _home() / ".claude" / "mcp.json",
            _home() / ".codex" / "config.toml",
            _home() / ".cursor" / "mcp.json",
        ]
    for ws in _workspace_roots():
        configs.append(ws / ".cursor" / "mcp.json")
        configs.append(ws / ".mcp.json")

    servers: set[str] = set()
    for cfg in configs:
        if not cfg.is_file():
            continue
        try:
            text = cfg.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if cfg.suffix == ".json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            mcp = data.get("mcpServers") or data.get("servers") or {}
            if isinstance(mcp, dict):
                servers.update(str(k) for k in mcp.keys())
        else:
            for m in re.finditer(r"(?:mcp_servers|mcpServers)[\.\[][\"']?([A-Za-z0-9_-]+)", text):
                servers.add(m.group(1))

    items = []
    for name in sorted(servers):
        chars = 80 * 4
        items.append(
            {
                "kind": "mcp",
                "path": f"mcp:{name}",
                "name": name,
                "chars": chars,
                "tok_k": _tok(chars),
            }
        )
    return items


def _fingerprint(workspaces: list[Path]) -> str:
    parts = [str(p.resolve()) for p in workspaces]
    parts.append(str(_home()))
    return "|".join(sorted(parts))


def measure() -> dict:
    workspaces = _workspace_roots()
    rules = _collect_rules(workspaces)
    skills = _collect_skills(workspaces)
    mcp = _collect_mcp()

    rules_k = round(sum(i["tok_k"] for i in rules), 2)
    skills_k = round(sum(i["tok_k"] for i in skills), 2)
    mcp_k = round(sum(i["tok_k"] for i in mcp), 2)
    total_k = round(rules_k + skills_k + mcp_k, 2)

    all_items = rules + skills + mcp
    top = sorted(all_items, key=lambda x: -x["tok_k"])[:TOP_N]

    return {
        "schema": 1,
        "measured_at": int(time.time()),
        "fingerprint": _fingerprint(workspaces),
        "workspaces": [str(w) for w in workspaces],
        "user_overhead_k": total_k,
        "layers": {
            "always_rules_k": rules_k,
            "skill_descriptions_k": skills_k,
            "mcp_k": mcp_k,
        },
        "counts": {
            "rules": len(rules),
            "skills": len(skills),
            "mcp": len(mcp),
        },
        "top_offenders": top,
        "thresholds": {"immediate_k": 20, "deferred_k": 20, "deferred_turn": 10},
        "note": (
            "Disk inventory of user-controlled surface (deduped by name; skips ._disabled; "
            "Cursor host skips ~/.claude/plugins/cache). Prompt introspection is ground truth when auditing."
        ),
    }


def load_or_measure() -> dict:
    cache = _temp_cache()
    if not FORCE and cache.is_file():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            age = time.time() - float(data.get("measured_at") or 0)
            if age < CACHE_TTL_SEC and data.get("fingerprint") == _fingerprint(_workspace_roots()):
                data["cache_hit"] = True
                return data
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    data = measure()
    data["cache_hit"] = False
    try:
        cache.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass
    return data


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    try:
        data = load_or_measure()
    except Exception as e:
        data = {
            "schema": 1,
            "error": str(e),
            "user_overhead_k": 0,
            "layers": {},
            "top_offenders": [],
            "cache_hit": False,
        }
    print(json.dumps(data, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
