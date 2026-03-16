# migros-shopping

*Let your AI agent do the grocery run.*

A Claude Code skill that automates shopping on [migros.ch](https://www.migros.ch) — search products, build a cart, and get a shareable list link. Pure API calls, no browser needed.

---

## Requirements

- Python 3.9+
- `curl_cffi` (`pip install curl_cffi`)
- A Migros account (no MFA)

---

## Setup

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

---

## Usage

Ask Claude:

> "Fill my Migros cart with: lactose free milk, spaghetti, tomatoes, bread, and butter."

The skill will log in, create a fresh list, search for each product, add them to the cart, and return a share link like `https://www.migros.ch/list/aBcDeFgH`.

Pro tip: Export your previous orders to tell your agent about your prefered products.

### Manual CLI usage

```bash
bash scripts/migros-login.sh
python3 scripts/migros-api.py newlist "Einkauf"
bash scripts/migros-search.sh "Vollmilch"
bash scripts/migros-add.sh 100005465
bash scripts/migros-cart.sh
python3 scripts/migros-api.py share
```

---

## Claude Code / OpenClaw

Drop this directory into your skills folder. `SKILL.md` is discovered automatically.
