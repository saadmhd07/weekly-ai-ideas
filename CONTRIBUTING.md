# Contributing

## Objectif Du Projet

Le projet doit rester simple, local-first et utile pour générer une newsletter hebdomadaire courte d'idées GenAI buildables.

Priorités produit:

- idées synthétiques et actionnables
- sources faciles à maintenir
- dépendances minimales
- exécution locale ou cron simple
- pas de plateforme lourde tant que ce n'est pas nécessaire

## Setup Local

```bash
cp .env.example .env
python3 -m compileall genai_newsletter
```

Pour générer une ideabox:

```bash
python3 -m genai_newsletter.cli collect --limit 80
python3 -m genai_newsletter.cli ideabox --days 7
```

Pour tester l'email:

```bash
python3 -m genai_newsletter.cli send
```

## Structure

```text
genai_newsletter/
  collectors/   sources de signaux
  cli.py        commandes CLI
  config.py     configuration JSON
  emailer.py    rendu/envoi email SMTP
  env.py        chargement .env
  ideabox.py    prompt, schéma OpenAI, rendu Markdown court
  pipeline.py   enrichissement, scoring, clustering
  storage.py    SQLite signals
```

## Ajouter Une Source

1. Créer un collecteur dans `genai_newsletter/collectors/`.
2. Retourner des objets `Signal` normalisés.
3. Ajouter le collecteur dans `build_collectors()` dans `cli.py`.
4. Vérifier que la source échoue proprement sans casser les autres.
5. Tester avec une petite limite:

```bash
python3 -m genai_newsletter.cli collect --limit 5
```

## Modifier Le Prompt Ou Le Format

Le format principal est dans `genai_newsletter/ideabox.py`:

- `IDEABOX_SCHEMA`: contrat JSON attendu d'OpenAI
- `build_instructions()`: comportement éditorial
- `build_wide_input()`: compression des signaux
- `render_ideabox()`: Markdown final

Garder la sortie courte. Si une section n'est pas lue en moins de 3 minutes, elle est probablement trop longue.

## Validation

Avant de considérer un changement terminé:

```bash
python3 -m compileall genai_newsletter
python3 -m genai_newsletter.cli --help
python3 -m genai_newsletter.cli ideabox --help
```

Si le changement touche les collecteurs ou l'email, tester la commande concernée.

## Données Et Secrets

Ne jamais versionner:

- `.env`
- `data/*.db`
- `output/*.md`
- clés API ou mots de passe SMTP

Ces fichiers sont ignorés par `.gitignore`.

## Style

- Python standard library first.
- Pas de dépendance ajoutée sans raison claire.
- Erreurs réseau tolérées par source.
- Logs courts mais utiles.
- Préférer des fonctions simples et testables.
