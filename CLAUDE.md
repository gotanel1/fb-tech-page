# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A bot that reads tech news from RSS feeds, has Gemini write a Thai-language Facebook post about the
best article, and publishes it to a Facebook Page via the Graph API. It runs for free on a schedule
via GitHub Actions — there is no server to operate. All user-facing docs (README.md, SETUP.md) and
code comments are written in Thai; keep that convention when touching this repo.

## Commands

```bash
pip install -r requirements.txt

python src/main.py --dry-run              # fetch + let Gemini write, but don't post or call FB API
python src/main.py --dry-run --limit 3    # dry run, preview 3 candidate posts
python src/main.py                        # real run: fetch, write, publish, and record state
python tools/get_token.py                 # interactive helper to exchange a short-lived user
                                           # token for a permanent Page access token
```

There is no test suite, linter, or build step configured. `--dry-run` is the primary way to verify
changes: it exercises feed fetching, scoring, dedup, and (if `GEMINI_API_KEY` is set) the real Gemini
call, while skipping `FB_PAGE_ID`/`FB_PAGE_TOKEN` requirements and any Graph API/state writes.

Config comes from a `.env` file (copy `.env.example`) for local runs, or from GitHub repo
Secrets/Variables when running in Actions — see `src/config.py` for every variable read and its
default.

## Architecture

`src/main.py` is the only entrypoint and orchestrates a linear pipeline; each other module in `src/`
is a single stage with no cross-dependencies except through the `Article` dataclass and `Config`:

1. **`config.py`** — loads `.env` (via python-dotenv) plus `feeds.yaml`, and pre-reads `style.md` as a
   plain string into `Config.style_guide`. This is the only module that touches env vars or these
   files; everything else receives a `Config` instance.
2. **`news.py`** — fetches every feed in `feeds.yaml`, filters by `max_age_hours` and `blocklist`,
   scores each article (`score()`: freshness × feed weight × keyword `boost` multiplier × summary-length
   factor), then deduplicates across feeds using the same `url_key`/`title_key` fingerprints as the
   posted-history store before returning articles sorted best-first. `enrich()` is called later,
   per-article, to scrape the article's own page for fuller body text when the RSS summary is thin —
   it's a fetch-page-then-strip-tags-and-boilerplate best-effort scrape, not required for the pipeline
   to work.
3. **`writer.py`** — sends the article body plus the *entire contents of `style.md`* as a system
   prompt to Gemini (`generateContent` REST endpoint, model from `GEMINI_MODEL`), then strips markdown
   artifacts, quote wrapping, em dashes, and any stray URLs from the response. This is the only place
   that talks to Gemini. Retries 429/5xx up to 3 times with backoff.
4. **`facebook.py`** — thin wrapper (`PageClient`) around Graph API `POST /{page-id}/feed` and
   `POST /{post-id}/comments`, raising `FacebookError` on any non-2xx or `{"error": ...}` response.
5. **`state.py`** — `PostedStore` is the anti-duplicate-posting mechanism, backed by
   `state/posted.json`. Two independent fingerprints are tracked per article: `url_key` (SHA1 of the
   URL with tracking params like `utm_*`/`fbclid` stripped and `www.`/trailing slash normalized) and
   `title_key` (SHA1 of the sorted set of significant title words, so near-duplicate headlines from
   different outlets about the same story are also caught). Entries older than `KEEP_DAYS` (45) are
   pruned on every `save()`.

`main.run()` ties it together: `news.collect()` → skip anything `store.seen()` → `news.enrich()` →
`writer.write_post()` → publish via `PageClient` → `store.add()` + `store.save()`. `POST_STYLE`
controls whether the link is attached directly to the post (`link`, gets an FB link preview) or
posted as the first comment underneath a link-free post (`comment`, the default — better organic
reach). The loop stops once `cfg.posts_per_run` articles have been successfully published, not after
`cfg.posts_per_run` attempts.

### Editing bot behavior without touching code

- `style.md` — the page's persona/tone/format rules, read fresh on every `Config.load()` and injected
  verbatim into the Gemini system prompt. This is the primary lever for changing what posts sound
  like.
- `feeds.yaml` — RSS sources (with per-feed `weight` and `tag`), a `blocklist` of substrings that
  cause an article's title to be skipped entirely, and a `boost` map of keyword → score multiplier.
- `.github/workflows/post.yml` — cron schedule (UTC; Thailand is UTC+7) and the `workflow_dispatch`
  dry-run toggle for manual runs from the Actions tab.

### Repo quirk to know about

The GitHub Actions workflow currently exists as `.github/workflows/post.yml.txt` (inert — GitHub only
picks up `.yml`/`.yaml`) with an identical copy at `Claude outputs/post.yml`. Renaming/moving one into
`.github/workflows/post.yml` is what actually activates scheduled posting; don't assume the workflow
is live just because the file exists in the repo.

### Secrets

`FB_PAGE_ID`, `FB_PAGE_TOKEN`, `GEMINI_API_KEY` are required for real posting (`Config.require_for_posting()`
enforces this, but only when `dry_run` is false). `.env` is gitignored. Never commit real tokens —
`tools/get_token.py` exists specifically so a permanent Page token can be generated locally and pasted
into `.env`/GitHub Secrets rather than hand-copied from Graph API Explorer.
