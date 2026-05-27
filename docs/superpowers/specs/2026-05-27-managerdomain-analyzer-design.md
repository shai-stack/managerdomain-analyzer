# MANAGERDOMAIN Analyzer — Design Spec
**Date:** 2026-05-27  
**Status:** Approved

## Overview

A local web app that accepts up to 250 publisher domains, fetches each domain's `ads.txt` file, extracts all `MANAGERDOMAIN=` entries, and presents a summary table plus a grouped breakdown — all launchable via a double-click `launch.command`.

---

## Architecture

### Files

| File | Purpose |
|---|---|
| `app.py` | Flask server — serves UI and handles `/analyze` POST endpoint |
| `templates/index.html` | Single-page browser UI |
| `requirements.txt` | `flask`, `aiohttp` |
| `launch.command` | Installs deps, starts Flask on port 5050, opens browser |

### Data Flow

1. User pastes up to 250 domains (one per line) into textarea and clicks "Analyze"
2. Browser POSTs domain list as JSON to `POST /analyze`
3. Flask fetches `https://{domain}/ads.txt` for all domains **concurrently** using `aiohttp` + `asyncio`
4. Each ads.txt is scanned for lines starting with `MANAGERDOMAIN=` (case-insensitive); all values collected
5. JSON response returned: `[{ domain, manager_domains: [...] }, ...]`
6. Browser renders summary panel + full table

---

## UI

### Input Section
- Large textarea (placeholder: "Paste domains here, one per line")
- Live counter: "X / 250 domains" — warns if over 250, caps at 250
- "Analyze" button — disabled during fetch
- Progress indicator during fetch: "Analyzing X / 250 domains…" with a progress bar

### Summary Panel (rendered first)
- Table/cards grouped by MANAGERDOMAIN, sorted by frequency (descending)
- Each row shows: MANAGERDOMAIN | domain count
- Clicking a row filters the full table to show only those domains
- "None" group included so missing data is visible

### Full Results Table
- Columns: `Domain` | `MANAGERDOMAIN(s)`
- Domains with "None" shown in muted style
- Multiple MANAGERDOMAINs for one domain shown comma-separated
- "Export CSV" button above the table

---

## ads.txt Parsing

- Fetch URL: `https://{domain}/ads.txt`, fallback to `http://{domain}/ads.txt` on failure
- Scan each line for prefix `MANAGERDOMAIN=` (case-insensitive)
- Extract value after `=`, trim whitespace
- Collect all matching lines (there may be multiple per file)
- If no matching lines found → `manager_domains: []` (shown as "None" in UI)

---

## Error Handling & Edge Cases

| Scenario | Behavior |
|---|---|
| ads.txt not found (404) | Show `None` |
| Domain unreachable / timeout (>10s) | Show `Error` in red |
| ads.txt exists, no MANAGERDOMAIN lines | Show `None` |
| Multiple MANAGERDOMAIN lines | Show all, comma-separated |
| Duplicate domains in input | Deduplicated silently before fetching |
| More than 250 domains | Warning shown; first 250 processed |
| HTTPS fails, HTTP available | Fallback to HTTP automatically |

---

## Technical Notes

- Concurrency: all domains fetched in parallel via `asyncio.gather` — 250 domains should complete in 5–15 seconds depending on network
- Fetch timeout: 10 seconds per domain
- Flask runs on port 5050 to avoid conflicts
- No external database or persistent storage — results exist only in the current browser session
- Future: can be made public by adding a backend proxy layer; the `/analyze` endpoint is already self-contained for that migration
