"""Site validation for rjbrooks-portfolio.

Checks every HTML file:
- exists and isn't truncated (closing </html> tag, minimum size)
- contains required Open Graph + Twitter Card meta tags
- internal href/src paths resolve to existing files in the repo
- contact section is present (catches the truncation bug we hit pre-CI)

Run from the repo root:

    python .github/scripts/site_check.py

Exits with status 1 if any check fails. Designed to be invoked from CI.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# === Per-repo manifest ===

REQUIRED_FILES = [
    "index.html",
    "og-image.png",
]

REQUIRED_META = {
    "index.html": [
        ("og:title",       r'<meta\s+property="og:title"\s+content="[^"]+"'),
        ("og:description", r'<meta\s+property="og:description"\s+content="[^"]+"'),
        ("og:image",       r'<meta\s+property="og:image"\s+content="[^"]+"'),
        ("og:url",         r'<meta\s+property="og:url"\s+content="[^"]+"'),
        ("twitter:card",   r'<meta\s+name="twitter:card"\s+content="[^"]+"'),
    ],
}

# Required structural sections — catches truncation that doesn't trip
# the closing-tag check (e.g. a file cut off mid-section but somehow ending OK)
REQUIRED_SECTIONS = {
    "index.html": [
        ("about heading",       r"<h2[^>]*>about</h2>"),
        ("currently heading",   r"<h2[^>]*>currently</h2>"),
        ("contact heading",     r"<h2[^>]*>contact</h2>"),
        ("footer with date",    r'class="meta">// last updated'),
    ],
}

MIN_HTML_SIZE_BYTES = 6000  # portfolio runs ~8.5KB; below 6KB is suspicious


# === Implementation ===

errors: list[str] = []


def check_required_files(repo_root: Path) -> None:
    for f in REQUIRED_FILES:
        p = repo_root / f
        if not p.exists():
            errors.append(f"Missing required file: {f}")


def check_html_well_formed(repo_root: Path) -> None:
    for html_path in sorted(repo_root.glob("*.html")):
        text = html_path.read_text(encoding="utf-8")
        size = len(text.encode("utf-8"))
        if size < MIN_HTML_SIZE_BYTES:
            errors.append(
                f"{html_path.name}: suspiciously small ({size} bytes); might be truncated"
            )
        if not text.rstrip().endswith("</html>"):
            errors.append(
                f"{html_path.name}: doesn't end with </html> tag; file may be truncated"
            )


def check_meta_tags(repo_root: Path) -> None:
    for filename, required_patterns in REQUIRED_META.items():
        path = repo_root / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for tag_name, pattern in required_patterns:
            if not re.search(pattern, text):
                errors.append(f"{filename}: missing required meta tag {tag_name}")


def check_required_sections(repo_root: Path) -> None:
    for filename, required_patterns in REQUIRED_SECTIONS.items():
        path = repo_root / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for section_name, pattern in required_patterns:
            if not re.search(pattern, text):
                errors.append(
                    f"{filename}: missing required section '{section_name}' "
                    f"(pattern: {pattern})"
                )


def check_internal_links(repo_root: Path) -> None:
    href_pattern = re.compile(r'(?:href|src)=["\']([^"\'#?]+)', re.IGNORECASE)
    for html_path in sorted(repo_root.glob("*.html")):
        text = html_path.read_text(encoding="utf-8")
        for match in href_pattern.finditer(text):
            url = match.group(1)
            if "://" in url or url.startswith(("mailto:", "tel:", "data:", "#")):
                continue
            local_path = url.split("?")[0].split("#")[0]
            if local_path.startswith("/"):
                local_path = local_path[1:]
            if not local_path:
                continue
            target = repo_root / local_path
            if not target.exists():
                target_html = repo_root / f"{local_path}.html"
                if not target_html.exists():
                    errors.append(
                        f"{html_path.name}: broken internal link to /{local_path}"
                    )


def main() -> int:
    repo_root = Path(".").resolve()
    print(f"Site check on {repo_root}")
    print(f"Files in root: {[p.name for p in sorted(repo_root.iterdir()) if p.is_file()]}")
    print()
    check_required_files(repo_root)
    check_html_well_formed(repo_root)
    check_meta_tags(repo_root)
    check_required_sections(repo_root)
    check_internal_links(repo_root)

    if errors:
        print(f"\nFAIL: {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("\nPASS: all site checks succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
