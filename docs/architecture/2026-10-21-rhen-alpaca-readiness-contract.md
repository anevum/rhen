# RHEN V5 / 2027 — Read-only Alpaca and capital continuity acceptance

Session: ANEVUM.RHEN.BUILD.2026-10-21.002.ALPACA-CAPITAL-READINESS
Change set: additive to draft PR #493 (stacked on #490 and #488).
Runtime state: OFF / NOT CONNECTED / NOT DEPLOYED. Synthetic tests are not brokerage acceptance.

## Implemented offline contracts

1. next_rhen/portfolio/alpaca_snapshot.py normalizes explicit GET /v2/account and GET /v2/positions responses. A private account ID binding must match before positions are read. Output shows UTC timestamp, currency, signed long and short market value, account blocked flags and the non-atomic read warning. It omits real account identifiers. It never declares broker cash to be family or business cash.
2. next_rhen/portfolio/alpaca_oauth_read_port.py is an opt-in server-side HTTP port restricted to two GET paths, explicit PAPER/LIVE origins, redirects disabled, bounded response size, proxy environment ignored and generic upstream errors. It contains no order, transfer or write method. It is not an OAuth consent flow, an active brokerage connection, or proof of a limited token scope.
3. next_rhen/finance/capital_readiness.py derives a declared surplus/shortfall within ONE funding domain: HOUSEHOLD or ANEVUM_BUSINESS. Inputs are decimal USD strings from independent authorized reviews. The liquid balance includes any restricted cash, which is deducted along with distinct, non-overlapping 90-day obligations, reserve floor, tax holdback and debt commitments. Missing inputs do not default to zero; stale reviews older than 30 days require refresh.
4. next_rhen/portfolio/theme_projection.py computes analyst-declared exclusive technology exposure within long US-equity/ETF holdings only. Missing classification remains unknown. Sources are submitted analyst links and not independently verified. The denominator is gross long USD equity holdings, not portfolio equity, buying power or household net worth.

## Hard authority boundaries

Authenticated, server-verified owner and workspace membership must precede every private read. Founder-only records must never flow into member workspaces. A future private consent flow must prove strict read-only Alpaca permissions; its server-side OAuth bearer must live in a separate secret vault and never be sent to browsers, ChatGPT prompts, public logs, or Git history.

The available Alpaca plugin exposes market-data tools, not this user's verified current brokerage portfolio. No real account data was accessed by this development change. IBKR is historical, not the active broker.

A positive declared financial surplus, recent broker snapshot, or complete theme classification NEVER permits transfers, deposits, orders, rebalancing, live strategy changes or expansion of risk limits. All projections explicitly report zero execution authority. Household reserves and business capital cannot be pooled or inferred from Alpaca buying power.

There are no production routes, new databases, migrations, provider secrets, Cloudflare or Railway deployments in this change. Never import this module into the legacy founder live execution path.

## Acceptance gates

A. Review prerequisites #488 and #490 and all #493 changes, exact-head tests and independent security review.

B. Review and authorize private read-only OAuth consent, token scope and revocation, expiry/refresh, owner-to-account binding, least privilege and failure modes before connecting an actual Alpaca account.

C. Accept real consenting-owner data, provider receipt timing, completeness, error/failure and reconciliation; reject mismatched account, short or non-equity scope misrepresentation and stale timestamps.

D. Explicitly authorize independent private household and business ledger connections, resolve possible double counted obligations, and obtain financial review. No private balances belong in the public repository.

E. Implement a protected RHEN member/founder dashboard after authenticated tenant separation, privacy/security review, mobile accessibility, actual iPhone Safari testing, and rollback acceptance.

The self-contained design prototype under docs/prototypes contains synthetic, fictional allocations and no account/data connection.

No merge, credential provisioning or deployment authorization is granted.
