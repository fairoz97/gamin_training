# Garmin dashboards

Four single-file dashboards built from your Garmin Personal API data:

| page | what it is |
|---|---|
| `commander.html` | mission-control view: vitals, fitness/fatigue/form, weekly km |
| `coach.html` | what a coach checks before messaging you: flags, drafted note, volume, intensity |
| `tinkerer.html` | interactive run explorer (pace vs heart rate) |
| `brain.html` | your training as a glowing 3D graph |

## Setup

```bash
pip install -r requirements.txt
echo "GARMIN_PERSONAL_API_KEY=your-key-here" > .env     # .env is git-ignored
cp config.example.json config.json                       # race, name: edit to taste (git-ignored)
python pull.py                                           # writes data/garmin.json
python build_all.py                                      # writes the four dashboards
```

Open any `*.html` by double-click, or use `index.html` as a launcher.

## Refresh button

Every dashboard has a **↻ REFRESH** button. It needs the local server:

```bash
python serve.py        # opens http://127.0.0.1:8765/
```

Clicking the button re-runs `pull.py` and `build_all.py`, then reloads the page.
Opened straight from disk it only tells you to start `serve.py`.

## Putting it on GitHub

The repo is set up to hold the **code only**. `.env`, `data/`, `config.json` and the built
`*.html` files are git-ignored, because they contain your API key and your health data.

```bash
git init -b main
git add .
git status        # check: no .env, no data/, no commander/coach/tinkerer/brain .html
git commit -m "Garmin dashboards"

# with the GitHub CLI:
gh repo create garmin-dashboards --private --source . --push

# or create an empty PRIVATE repo on github.com, then:
git remote add origin https://github.com/<you>/garmin-dashboards.git
git push -u origin main
```

### Optional: publish to GitHub Pages

`.github/workflows/pages.yml` can pull your data and publish the dashboards. It is manual-only
and off by default. **A Pages site is public to anyone with the link**, even when the repository is
private (private Pages needs GitHub Enterprise Cloud), and the pages embed your heart rate, HRV,
sleep and activity history. Only enable it if you are fine with that.

1. Repo **Settings > Pages > Source: GitHub Actions**.
2. Repo **Settings > Secrets and variables > Actions**: add `GARMIN_PERSONAL_API_KEY`.
3. **Actions** tab: run *Build and publish dashboards*. Uncomment the `schedule:` lines for a daily refresh.

On a hosted page the button reads **↻ RELOAD** and simply fetches the last published version.

## Opening the dashboards on your phone

Phones can't run `serve.py`, so use a hosted copy (GitHub Pages). **The site is public to anyone with the link and the
pages embed your health data.** `publish_site.py` adds a `noindex` tag so search engines skip it, but that is not protection.

```bash
python pull.py
python publish_site.py          # builds everything into docs/
git add -f docs                 # -f on purpose: docs/ is git-ignored by default
git commit -m "Update dashboards" && git push
```

Then **Settings > Pages > Source: Deploy from a branch > `main` / `/docs`**. Your link will be
`https://<you>.github.io/<repo>/`. Bookmark it on your phone. To update the data, re-run the four lines above.
(GitHub Free only publishes Pages from public repositories.)
