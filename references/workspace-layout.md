# Workspace layout — one working folder per business, nothing scattered

Reusable, business-agnostic. Every skill in the suite READS and WRITES inside a single **working folder**
per business (or per account-group). Nothing is written into the plugin, into `D:\tmp`, `/tmp`, or random
locations. A user who installs the plugin and runs `/google-ads` gets ONE tidy folder — not files sprinkled
across their disk.

## The folder (create on first run, reuse forever)
```
<workdir>/                      # e.g. ~/ads/<business>/  or  <business>-ads/   (user picks; setup confirms it)
  account-context.yaml          # THE backbone — business facts + the connections registry (below)
  CONNECTIONS.md                # optional human-readable map: which connector/token each source uses + how to run it
  raw/                          # large raw API pulls (bundle inputs). Safe to delete/regenerate.
  audits/<YYYY-MM-DD>/          # AUDIT.html, bundle.json, audit-result.json, MONEY-LEAK-REPORT.md, DETAILED-ACCOUNT-REPORT.md
  measurement/<YYYY-MM-DD>/     # MEASUREMENT-REPORT.md
  plans/<YYYY-MM-DD>/           # GOOGLE-ADS-PLAN.md
  builds/<campaign>/            # campaign-spec.json, blueprint.xlsx, editor CSVs
  changes/<YYYY-MM-DD>/         # change-set.json, CHANGE-PLAN.md, negatives CSVs
  scripts/                      # any one-off helper this business needed
```
- The script tools already take `--out-dir`; always point them at the right subfolder above.
- Date-stamp the per-run folders so history is kept, not overwritten.
- `setup` creates `<workdir>` + `account-context.yaml` and confirms the path with the user FIRST.

## Multi-site: shared vs per-site
- **Option A — separate (simplest):** one `<workdir>` per site (`acme-us/`, `acme-eu/`), each with its own
  `account-context.yaml`. Use when sites share almost nothing.
- **Option B — shared parent:** one parent folder + per-site subfolders + a `shared/` folder; the
  `account-context.yaml` `shared` block declares what is shared (one customer-match list, one GSC property,
  one MCC) vs split per site. Use when sites share assets/accounts.
- Decide this in `setup` (STEP 2 multi-site question) and record it in `shared.enabled` + `shared.shared_assets`.

## Secrets & connectors — pointers, never copies (NON-NEGOTIABLE)
The suite needs tokens (Google Ads, store Admin, GA4, Merchant) but must NOT scatter or leak them.
- **NEVER copy a raw API token/key into the working folder, an output, a report, or `account-context.yaml`.**
- The **connections registry** in `account-context.yaml` records, per source, *how to reach it* — a POINTER
  read at runtime, not the secret:
  ```yaml
  connections:
    google_ads: { status: connected, via: "mcp:<server-id>" }
    store:      { status: connected, via: "env:/abs/path/.env#SHOPIFY_ADMIN_TOKEN_2" }   # key NAME, not value
    ga4:        { status: connected, via: "script:ktb-data-hub  GA4Hub('nd')  prop=318105347" }
    merchant:   { status: connected, via: "server:/abs/path/google-merchant-mcp (venv + ADC json)", id: "585732301" }
    gsc:        { status: missing,   via: "", guide: "connect Search Console" }
  ```
- If the user *wants* credentials kept locally, put them in a **gitignored** `secrets/` inside the workdir and
  point `via:` at the path — but the default is to reference an existing `.env`/secret store in place.
- **Never commit the working folder's secrets.** Add `secrets/`, `.env`, and `raw/` to `.gitignore` if the
  workdir is a repo.
- `CONNECTIONS.md` (optional, human-readable) can mirror the registry: "Merchant = run
  `projects/google-merchant-mcp` (venv + ADC); GMC id per brand" — so the operator knows where everything is.

## Connector shapes the hub recognizes (per role)
A connector can be any of these — `setup` records which one, with the path/id:
1. a **connected MCP** (`via: mcp:<id>`),
2. **API creds in a local env/secret file** (`via: env:/path/.env#KEY`),
3. a **runnable local server / script** (`via: server:/path (venv+ADC)` or `via: script:<proj> <entry>`),
4. **ask the user** (record what's still missing + the `guide`).
Merchant Center especially is often shape #3 — a runnable server (e.g. `google-merchant-mcp/server.py` with a
venv + ADC token) — use it for the D14 approval/disapproval/GTIN layer; record its path + GMC id, not the token.
