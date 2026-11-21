# Setup

1. The repo **JanBartos6** holds this card; GitHub shows its README on your profile.
2. Create a classic personal access token (Settings → Developer settings → Tokens (classic)) with the **repo** and **read:user** scopes. `repo` lets private repos such as JetGoal count towards commits and languages; their names and code never appear on the card.
3. In the JanBartos6 repo: Settings → Secrets and variables → Actions → New repository secret, name `ACCESS_TOKEN`.
4. Actions tab → "Update profile card" → Run workflow. After that it refreshes daily.
   Until the secret exists, the workflow skips the stats step and keeps the committed numbers.

## Changing things

- **Text on the card:** edit `card.json`. Lines are right-aligned automatically.
- **ASCII art:** `pip install pillow`, then `python scripts/ascii_from_image.py your-photo.jpg --cols 42`.
  Use a tightly cropped photo on a plain background (or a high-contrast JetGoal frame).
  Try `--gamma 0.8` / `1.3` to brighten or darken. For logos or graphics add `--no-invert`.
- **Re-render locally:** `python scripts/render.py` (standard library only).
- Once JetGoal has a public page, point the "JetGoal beta key" link in `README.md` at it.
