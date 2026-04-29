# Contributing

## Project Goal

The project should stay simple, local-first, and useful for generating a short weekly newsletter of buildable GenAI ideas.

Product priorities:

- concise and actionable ideas
- sources that are easy to maintain
- minimal dependencies
- local execution or simple cron automation
- no heavy platform until it is clearly needed

## Local Setup

```bash
cp .env.example .env
python3 -m compileall genai_newsletter
```

Generate an ideabox:

```bash
python3 -m genai_newsletter.cli collect --limit 80
python3 -m genai_newsletter.cli ideabox --days 7
```

Test email delivery:

```bash
python3 -m genai_newsletter.cli send
```

## Structure

```text
genai_newsletter/
  collectors/   signal sources
  cli.py        CLI commands
  config.py     JSON configuration
  emailer.py    SMTP email rendering and delivery
  env.py        .env loader
  ideabox.py    OpenAI prompt, schema, and short Markdown rendering
  pipeline.py   enrichment, scoring, clustering
  storage.py    SQLite signal storage
```

## Add A Source

1. Create a collector in `genai_newsletter/collectors/`.
2. Return normalized `Signal` objects.
3. Register the collector in `build_collectors()` in `cli.py`.
4. Make sure source failures do not break other sources.
5. Test with a small limit:

```bash
python3 -m genai_newsletter.cli collect --limit 5
```

## Change The Prompt Or Format

The main format lives in `genai_newsletter/ideabox.py`:

- `IDEABOX_SCHEMA`: expected OpenAI JSON contract
- `build_instructions()`: editorial behavior
- `build_wide_input()`: signal compression
- `render_ideabox()`: final Markdown

Keep the output short. If a section cannot be read in under 3 minutes, it is probably too long.

## Validation

Before considering a change complete:

```bash
python3 -m compileall genai_newsletter
python3 -m genai_newsletter.cli --help
python3 -m genai_newsletter.cli ideabox --help
```

If the change touches collectors or email, test the relevant command.

## Data And Secrets

Never commit:

- `.env`
- `data/*.db`
- `output/*.md`
- API keys or SMTP passwords

These files are ignored by `.gitignore`.

## Style

- Prefer the Python standard library.
- Do not add dependencies without a clear reason.
- Network failures should be isolated per source.
- Logs should be short but useful.
- Prefer simple, testable functions.
