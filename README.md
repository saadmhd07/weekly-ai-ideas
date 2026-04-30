# GenAI Newsletter / Idea Box

Collects public GenAI signals, compresses them into inspiration cards, and generates a short twice-weekly side-project newsletter with OpenAI. The workflow can also email the result twice per week.

## Output

`ideabox` writes a short Markdown file to `output/ideabox-*.md` with:

- 3-4 TL;DR bullets
- 1 idea to ship this week
- 5 ideas maximum
- 2 ideas to avoid
- a few key source signals

Each idea includes: category, pitch, why it matters, MVP, distribution, monetization, and a `/10` score.

## Setup

```bash
cp .env.example .env
```

At minimum, set:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.2
```

For email delivery, also set:

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
SMTP_TLS=true
EMAIL_FROM=from@example.com
EMAIL_TO=to@example.com
```

`.env` is loaded automatically and is not committed.

## Main Commands

Collect signals:

```bash
python3 -m genai_newsletter.cli collect --limit 80
```

Generate the short idea box:

```bash
python3 -m genai_newsletter.cli ideabox --days 7
```

Email the latest `ideabox`:

```bash
python3 -m genai_newsletter.cli send
```

Full scheduled workflow: collect, generate, email:

```bash
python3 -m genai_newsletter.cli weekly
```

## Free Mode Without OpenAI

A heuristic newsletter mode exists without an LLM:

```bash
python3 -m genai_newsletter.cli run --limit 30 --days 7
```

This uses only public sources, but idea quality is much lower than `ideabox`.

## Included Sources

- Hacker News Algolia
- arXiv API
- GitHub Search API
- Reddit JSON endpoints
- RSS feeds configured in `config.example.json`

## Advanced Configuration

Copy the example config if you want to change sources, keywords, or weights:

```bash
cp config.example.json config.json
```

Local data is stored in:

```text
data/newsletter.db
```

Generated files are written to:

```text
output/
```

## Wide Mode

Wide mode is enabled by default. It compresses many signals into diverse inspiration cards before calling OpenAI.

Current defaults:

```text
--max-signals 120
--max-output-tokens 4000
--timeout 360
```

Disable wide mode and send rawer signals:

```bash
python3 -m genai_newsletter.cli ideabox --focused
```

## Email

Send a specific file:

```bash
python3 -m genai_newsletter.cli send --file output/ideabox-YYYY-MM-DD-HHMMSS.md
```

Emails are sent as plain text plus styled HTML.

## Weekly Automation

On Linux:

```bash
crontab -e
```

Example: every Monday and Thursday at 08:00:

```cron
0 8 * * 1,4 cd /home/saad/projects/newsletter && /usr/bin/python3 -m genai_newsletter.cli weekly >> /home/saad/projects/newsletter/output/weekly.log 2>&1
```

No deployment is required if your machine is on. If you want it to run while your computer is off, use a VPS, GitHub Actions with secrets, a NAS, or another always-on machine.

## Available Commands

```bash
python3 -m genai_newsletter.cli --help
```

Commands:

- `collect`: collect and store signals
- `newsletter`: generate the old heuristic newsletter from the local DB
- `ideabox`: generate the short OpenAI idea box
- `enrich`: recompute editorial notes for stored signals
- `send`: email a Markdown file
- `weekly`: collect, generate, and email
- `run`: collect and generate the heuristic newsletter

## Free Deployment With GitHub Actions

The repository includes a ready-to-use workflow:

```text
.github/workflows/weekly-newsletter.yml
```

It runs `python -m genai_newsletter.cli weekly --limit 80 --days 7` every Monday and Thursday at 08:00 UTC and can also be triggered manually from the GitHub Actions tab.

Configure this in GitHub:

Repository `Settings` -> `Secrets and variables` -> `Actions`.

Required secrets:

```text
OPENAI_API_KEY
SMTP_HOST
SMTP_USER
SMTP_PASSWORD
EMAIL_FROM
EMAIL_TO
```

Optional variables:

```text
OPENAI_MODEL=gpt-5.2
SMTP_PORT=587
SMTP_TLS=true
```

The GitHub runner is ephemeral: the SQLite database created during a run is not persisted. For this scheduled workflow, that is fine because the command collects, generates, and emails within the same run.

## Reddit

Reddit is currently consumed through RSS feeds in `rss_feeds`:

- `r/LocalLLaMA`
- `r/OpenAI`
- `r/MachineLearning`
- `r/SaaS`
- `r/Entrepreneur`

The older Reddit JSON collector is disabled by default because GitHub Actions runners are often blocked by Reddit with HTTP 403.

To re-enable it locally:

```bash
ENABLE_REDDIT_JSON=true python3 -m genai_newsletter.cli collect --limit 30
```
