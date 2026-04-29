# GenAI Newsletter / Idea Box

Collecte des signaux GenAI publics, les compresse en inspirations, puis génère une newsletter courte de side projects buildables avec OpenAI. Le workflow peut aussi envoyer le résultat par email une fois par semaine.

## Ce Que Ça Produit

`ideabox` génère un Markdown court dans `output/ideabox-*.md` avec:

- TL;DR en 3-4 bullets
- 1 idée à shipper cette semaine
- 5 idées maximum
- 2 idées à éviter
- quelques signaux clés

Chaque idée contient: catégorie, pitch, pourquoi, MVP, distribution, monétisation et score `/10`.

## Setup

```bash
cp .env.example .env
```

Renseigne au minimum:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.2
```

Pour l'email, ajoute aussi:

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
SMTP_TLS=true
EMAIL_FROM=from@example.com
EMAIL_TO=to@example.com
```

Le fichier `.env` est chargé automatiquement et n'est pas versionné.

## Commandes Principales

Collecter des signaux:

```bash
python3 -m genai_newsletter.cli collect --limit 80
```

Générer la boîte à idées courte:

```bash
python3 -m genai_newsletter.cli ideabox --days 7
```

Envoyer le dernier `ideabox` par email:

```bash
python3 -m genai_newsletter.cli send
```

Workflow complet hebdo: collecter, générer, envoyer:

```bash
python3 -m genai_newsletter.cli weekly
```

## Mode Gratuit Sans OpenAI

Une newsletter heuristique existe sans LLM:

```bash
python3 -m genai_newsletter.cli run --limit 30 --days 7
```

Ce mode utilise seulement des sources publiques, mais la qualité des idées est nettement inférieure au mode `ideabox`.

## Sources Incluses

- Hacker News Algolia
- arXiv API
- GitHub Search API
- Reddit JSON endpoints
- RSS configurable dans `config.example.json`

## Configuration Avancée

Copie la config d'exemple si tu veux modifier les sources, mots-clés ou poids:

```bash
cp config.example.json config.json
```

Les données locales sont stockées dans:

```text
data/newsletter.db
```

Les sorties sont écrites dans:

```text
output/
```

## Mode Wide

Le mode wide est activé par défaut. Il compresse beaucoup de signaux en cartes d'inspiration diversifiées avant d'appeler OpenAI.

Defaults actuels:

```text
--max-signals 120
--max-output-tokens 4000
--timeout 360
```

Désactiver wide et envoyer des signaux plus bruts:

```bash
python3 -m genai_newsletter.cli ideabox --focused
```

## Email

Envoyer un fichier précis:

```bash
python3 -m genai_newsletter.cli send --file output/ideabox-YYYY-MM-DD-HHMMSS.md
```

Le mail est envoyé en texte brut + HTML stylé.

## Automatisation Hebdomadaire

Sur Linux:

```bash
crontab -e
```

Exemple tous les lundis à 8h:

```cron
0 8 * * 1 cd /home/saad/projects/newsletter && /usr/bin/python3 -m genai_newsletter.cli weekly >> /home/saad/projects/newsletter/output/weekly.log 2>&1
```

Pas besoin de déployer si ta machine est allumée. Si tu veux que ça tourne même PC éteint, utilise un VPS, GitHub Actions avec secrets, un NAS ou une machine toujours allumée.

## Commandes Disponibles

```bash
python3 -m genai_newsletter.cli --help
```

Commandes:

- `collect`: collecte et stocke les signaux
- `newsletter`: génère l'ancienne newsletter heuristique depuis la DB
- `ideabox`: génère la boîte à idées courte avec OpenAI
- `enrich`: recalcule les notes éditoriales des signaux stockés
- `send`: envoie un Markdown par email
- `weekly`: collecte, génère et envoie par email
- `run`: collecte puis génère la newsletter heuristique

## Déploiement Gratuit Avec GitHub Actions

Le repo contient un workflow prêt à l'emploi:

```text
.github/workflows/weekly-newsletter.yml
```

Il lance `python -m genai_newsletter.cli weekly --limit 80 --days 7` tous les lundis à 08:00 UTC et peut aussi être déclenché manuellement depuis l'onglet GitHub Actions.

À configurer dans GitHub:

Repository `Settings` -> `Secrets and variables` -> `Actions`.

Secrets nécessaires:

```text
OPENAI_API_KEY
SMTP_HOST
SMTP_USER
SMTP_PASSWORD
EMAIL_FROM
EMAIL_TO
```

Variables optionnelles:

```text
OPENAI_MODEL=gpt-5.2
SMTP_PORT=587
SMTP_TLS=true
```

Le runner GitHub est éphémère: la base SQLite créée pendant l'exécution n'est pas conservée. Pour ce workflow hebdomadaire, ce n'est pas bloquant parce que la commande collecte, génère et envoie dans le même run.
