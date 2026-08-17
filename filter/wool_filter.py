#!/usr/bin/env python3
"""Filter wool_scripts modules: strip rules for sites that misbehave on Shadowrocket.

Sites are configured in wool_filter_config.json (domains + script names per site,
plus an `enabled` list). Only enabled sites are stripped.

Line-level logic (Surge .module format):
  - [Rule] / [URL Rewrite] / [Body Rewrite] / [Map Local]: drop lines containing
    any enabled-site domain (token-matched).
  - [Script]: additionally drop lines whose script name (before '=') is in the
    site's script list.
  - [MITM]: the `hostname = ...` line is comma-separated; drop matching entries
    instead of the whole line.
  - Comments containing site domains are dropped too (informational only).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "filter" / "wool_filter_config.json"

CONTENT_SECTIONS = {"[Rule]", "[URL Rewrite]", "[Body Rewrite]", "[Map Local]", "[Script]"}


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_matchers(config):
    """Return (domain_regexes, script_names, keywords) for enabled sites."""
    sites = config["sites"]
    enabled = config.get("enabled", [])
    domains, scripts, keywords = [], [], []
    for name in enabled:
        site = sites.get(name)
        if not site:
            print(f"[warn] enabled site '{name}' not defined in config", file=sys.stderr)
            continue
        for d in site.get("domains", []):
            bare = d.lower().lstrip(".")
            if bare:
                # match bare domain as a token: preceded by start / non-alnum
                domains.append(re.compile(r"(^|[^a-z0-9-])" + re.escape(bare)))
        scripts.extend(s.lower() for s in site.get("scripts", []))
        keywords.extend(k.lower() for k in site.get("keywords", []))
    return domains, sorted(set(scripts)), sorted(set(keywords))


def hit_domain(line, regexes):
    # normalize: Surge 规则里域名常写成正则转义形式 (bilibili\.com)，剥掉反斜杠再匹配
    low = line.lower().replace("\\", "")
    return any(r.search(low) for r in regexes)


def hit_keyword(line, keywords):
    low = line.lower().replace("\\", "")
    return any(k in low for k in keywords)


def filter_module(text, config):
    domains, script_names, keywords = build_matchers(config)
    removed = []
    out = []
    section = None
    for line in text.splitlines():
        stripped = line.strip()
        low = line.lower()
        if stripped.startswith("["):
            section = stripped
            out.append(line)
            continue
        # [MITM] hostname = %APPEND% a.com, b.com, ... → drop matching entries
        if section == "[MITM]" and low.startswith("hostname"):
            eq = line.find("=")
            if eq != -1:
                # 保留 = 后的空格（上游为 "hostname = %APPEND% ..."）
                prefix = line[: eq + 1] + (" " if len(line) > eq + 1 and line[eq + 1] in " \t" else "")
                entries = [e.strip() for e in line[eq + 1 :].split(",")]
                kept, dropped = [], 0
                for e in entries:
                    if e and (hit_domain(e, domains) or hit_keyword(e, keywords)):
                        dropped += 1
                    elif e:
                        kept.append(e)
                if dropped:
                    removed.append(line.strip())
                out.append(prefix + ", ".join(kept))
                continue
        # comments: drop if mentions a site (domain or display keyword e.g. 哔哩哔哩)
        if stripped.startswith("#"):
            if hit_domain(line, domains) or hit_keyword(line, keywords):
                removed.append(line)
            else:
                out.append(line)
            continue
        # [Script] name-based removal
        if section == "[Script]" and "=" in line:
            name = line.split("=", 1)[0].strip().lower()
            if name in script_names:
                removed.append(line)
                continue
        # domain-based removal in content sections
        if section in CONTENT_SECTIONS and hit_domain(line, domains):
            removed.append(line)
            continue
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else ""), removed


def main():
    config = load_config()
    domains, _, keywords = build_matchers(config)
    total = 0
    for target in config["targets"]:
        path = ROOT / target
        if not path.exists():
            print(f"[skip] {target} not found")
            continue
        original = path.read_text(encoding="utf-8")
        new_text, removed = filter_module(original, config)
        path.write_text(new_text, encoding="utf-8")
        total += len(removed)
        print(f"[ok] {target}: removed {len(removed)} lines ({len(original.splitlines())} -> {len(new_text.splitlines())})")
        for r in removed[:15]:
            print(f"      - {r.strip()[:110]}")
        if len(removed) > 15:
            print(f"      ... and {len(removed) - 15} more")
        # residue check: no remaining references to enabled-site domains
        residue = [l for l in new_text.splitlines() if hit_domain(l, domains) or hit_keyword(l, keywords)]
        if residue:
            print(f"[!!] RESIDUE: {len(residue)} lines still match enabled sites:")
            for r in residue[:10]:
                print(f"      ! {r.strip()[:110]}")
            sys.exit(1)
        print(f"     residue check: clean")
    print(f"[done] total removed: {total} lines")


if __name__ == "__main__":
    main()
