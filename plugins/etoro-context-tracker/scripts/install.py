#!/usr/bin/env python3
"""Cross-platform installer for etoro-context-tracker (Cursor / Claude / Codex).

Usage:
  python3 scripts/install.py [--target cursor|claude|codex|all]
  python3 scripts/install.py --target cursor --remove-global-rule
  python3 scripts/install.py --target cursor --also-sync-global-rule
  python3 scripts/install.py --python /usr/local/bin/python3

Thin wrappers: install.sh (macOS/Linux), install.ps1 (Windows).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PLUGIN_NAME = "etoro-context-tracker"
MARKETPLACE_NAME = "agentplugins"


def _home() -> Path:
    return Path.home()


def _plugin_root() -> Path:
    # scripts/ -> plugin root
    root = Path(__file__).resolve().parent.parent
    if not (root / ".cursor-plugin" / "plugin.json").is_file():
        raise SystemExit(f"plugin root not found (missing .cursor-plugin/plugin.json): {root}")
    return root


def _find_python(explicit: str | None) -> str:
    if explicit:
        p = Path(explicit)
        if not p.is_file():
            raise SystemExit(f"--python not found: {explicit}")
        return str(p.resolve())
    for name in ("python3", "python"):
        found = shutil.which(name)
        if not found:
            continue
        # Skip the Windows Store redirector stub when possible
        try:
            out = subprocess.run(
                [found, "-c", "import sys; print(sys.version_info.major)"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if out.stdout.strip() == "3":
                return found
        except (OSError, subprocess.SubprocessError):
            continue
    raise SystemExit("Need Python 3 on PATH (python3 or python). Or pass --python /path/to/python3")


def _rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _copy_plugin(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _rmtree(dest)
    shutil.copytree(src, dest)


def install_cursor(plugin_root: Path, *, also_sync_global: bool, remove_global: bool) -> None:
    if also_sync_global and remove_global:
        raise SystemExit("Pick one: --also-sync-global-rule or --remove-global-rule, not both.")

    dest = _home() / ".cursor" / "plugins" / "local" / PLUGIN_NAME
    global_rule = _home() / ".cursor" / "rules" / "context-tracker.mdc"
    _copy_plugin(plugin_root, dest)
    print(f"Cursor: installed -> {dest}")

    if also_sync_global:
        rules = _home() / ".cursor" / "rules"
        rules.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plugin_root / "rules" / "context-tracker.mdc", global_rule)
        print(f"Cursor: synced global fallback -> {global_rule}")
        print("WARNING: plugin + global both alwaysApply = ~2x tracker tokens. Prefer plugin-only after verify.")
    elif remove_global:
        if global_rule.is_file():
            global_rule.unlink()
            print(f"Cursor: removed global duplicate -> {global_rule} (plugin is source of truth)")
        else:
            print("Cursor: no global rule to remove (already clean)")
    elif global_rule.is_file():
        print(f"Cursor: global rule still present at {global_rule}")
        print("  After Reload Window confirms the plugin footer works, re-run with --remove-global-rule")

    print("Reload Cursor (Developer: Reload Window), then start a NEW chat.")
    print("Expect last line: ⚡ Turn 1 | ~…K chat / ~…K total | 🟢  (inside a one-line diff fence).")
    print("If missing after reload: re-run with --also-sync-global-rule")


def _marketplace_root(plugin_root: Path) -> Path:
    """Find the Claude marketplace root that contains this plugin.

    Supported layouts:
      - Public repo:  <repo>/.claude-plugin/marketplace.json  + plugins/<name>/
      - Lab nested:   <repo>/plugins/.claude-plugin/marketplace.json + <repo>/plugins/<name>/
    """
    for candidate in (plugin_root.parent.parent, plugin_root.parent):
        if (candidate / ".claude-plugin" / "marketplace.json").is_file():
            return candidate
    raise SystemExit(
        "Missing .claude-plugin/marketplace.json above the plugin "
        f"(looked in {plugin_root.parent.parent} and {plugin_root.parent})"
    )


def install_claude(plugin_root: Path) -> None:
    # Claude Code 2.1.x: persistent install = marketplace add + install name@marketplace.
    # Session-only: claude --plugin-dir <plugin_root>
    marketplace_root = _marketplace_root(plugin_root)

    claude = shutil.which("claude")
    if not claude:
        print("Claude CLI not on PATH. Install manually:")
        print(f'  claude plugin marketplace add "{marketplace_root}"')
        print(f"  claude plugin install {PLUGIN_NAME}@{MARKETPLACE_NAME}")
        print(f'  Or session-only: claude --plugin-dir "{plugin_root}"')
        return

    print(f"Claude: ensuring local marketplace '{MARKETPLACE_NAME}' -> {marketplace_root}")
    add = subprocess.run(
        [claude, "plugin", "marketplace", "add", str(marketplace_root)],
        capture_output=True,
        text=True,
    )
    if add.stdout.strip():
        print(add.stdout.rstrip())
    if add.stderr.strip():
        print(add.stderr.rstrip())

    spec = f"{PLUGIN_NAME}@{MARKETPLACE_NAME}"
    print(f"Claude: installing {spec}")
    inst = subprocess.run(
        [claude, "plugin", "install", spec],
        capture_output=True,
        text=True,
    )
    if inst.stdout.strip():
        print(inst.stdout.rstrip())
    if inst.stderr.strip():
        print(inst.stderr.rstrip())
    if inst.returncode != 0:
        print(f"Claude install failed (exit {inst.returncode}). Session-only fallback:")
        print(f'  claude --plugin-dir "{plugin_root}"')
    else:
        print("Claude: installed. Open a new Claude Code session to load hooks.")


def install_codex(plugin_root: Path, python: str) -> None:
    dest = _home() / ".codex" / "plugins" / PLUGIN_NAME
    _copy_plugin(plugin_root, dest)
    print(f"Codex: plugin files -> {dest}")

    hooks_file = _home() / ".codex" / "hooks.json"
    inject = dest / "scripts" / "inject_banner.py"
    merge_hooks = plugin_root / "scripts" / "merge_codex_hooks.py"
    result = subprocess.run(
        [python, str(merge_hooks), str(hooks_file), python, str(inject)],
        capture_output=True,
        text=True,
        check=False,
    )
    msg = (result.stdout or result.stderr or "").strip() or f"exit {result.returncode}"
    if result.returncode == 0 and msg == "MERGED":
        print(f"Codex: merged UserPromptSubmit hook into {hooks_file}")
    else:
        print(f"Codex: hook status: {msg}")

    agents = _home() / ".codex" / "AGENTS.md"
    merge_agents = plugin_root / "scripts" / "merge_codex_agents.py"
    snippet = plugin_root / "AGENTS.md"
    agents_result = subprocess.run(
        [python, str(merge_agents), str(agents), str(snippet)],
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"Codex: AGENTS.md {(agents_result.stdout or agents_result.stderr or '').strip()}")
    print("Restart Codex / open a new session to load hooks.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install etoro-context-tracker (Cursor / Claude / Codex)")
    parser.add_argument(
        "--target",
        "-t",
        choices=("cursor", "claude", "codex", "all"),
        default="all",
        help="Which IDE to install for (default: all)",
    )
    parser.add_argument(
        "--also-sync-global-rule",
        action="store_true",
        help="Cursor: also write ~/.cursor/rules/context-tracker.mdc (fallback if plugin rule does not load)",
    )
    parser.add_argument(
        "--remove-global-rule",
        action="store_true",
        help="Cursor: remove ~/.cursor/rules/context-tracker.mdc after plugin verify",
    )
    parser.add_argument(
        "--python",
        default=os.environ.get("ETORO_CONTEXT_TRACKER_PYTHON"),
        help="Python 3 executable for Codex hooks (default: python3/python on PATH)",
    )
    args = parser.parse_args(argv)

    plugin_root = _plugin_root()
    print(f"Plugin root: {plugin_root}")
    print(f"Platform: {sys.platform}  home: {_home()}")

    # Only resolve python when Codex (or all) needs it — Claude/Cursor don't require it for install.
    python = None
    if args.target in ("codex", "all"):
        python = _find_python(args.python)
        print(f"Python: {python}")

    if args.target in ("cursor", "all"):
        install_cursor(
            plugin_root,
            also_sync_global=args.also_sync_global_rule,
            remove_global=args.remove_global_rule,
        )
    if args.target in ("claude", "all"):
        install_claude(plugin_root)
    if args.target in ("codex", "all"):
        assert python is not None
        install_codex(plugin_root, python)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
