#!/usr/bin/env python3
"""Build every dashboard and copy the publishable set into docs/ (for GitHub Pages).

    python pull.py && python publish_site.py

Any extra flags are passed to build_all.py (e.g. --race 2027-03-14).
docs/ holds pages with your health data embedded: it is git-ignored on purpose, so adding it to a
repo is a deliberate step (git add -f docs). A Pages site is public to anyone with the link.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGES = ["index.html", "commander.html", "coach.html", "tinkerer.html", "brain.html"]
NOINDEX = '<meta name="robots" content="noindex,nofollow">'


def main():
    p = subprocess.run([sys.executable, "build_all.py"] + sys.argv[1:], cwd=HERE)
    if p.returncode:
        sys.exit("build_all.py failed; nothing published")
    out = HERE / "docs"
    out.mkdir(exist_ok=True)
    for name in PAGES:
        html = (HERE / name).read_text()
        if "<head>" in html:
            html = html.replace("<head>", "<head>\n" + NOINDEX, 1)
        (out / name).write_text(html)
    (out / ".nojekyll").write_text("")
    print(f"docs/ ready: {', '.join(PAGES)}")


if __name__ == "__main__":
    main()
