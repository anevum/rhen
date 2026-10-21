# RHEN / Continuance Investment Intelligence — 2027 product expansion

**Session:** `ANEVUM.RHEN.BUILD.2026-10-21.001.CONTINUANCE-INVESTMENT-INTELLIGENCE`  
**Decision state:** additive development proposal; not a V5 release or change to existing RHEN execution  
**Parent architecture:** [RHEN integrated engine decision](https://github.com/anevum/rhen/blob/design/anevum-vnext-greenfield-platform-20261009/docs/architecture/2026-10-10-rhen-integrated-prototype-consolidation.md)  
**Starting source:** successor draft [#490](https://github.com/anevum/rhen/pull/490), stacked on [#488](https://github.com/anevum/rhen/pull/488), **not merged**  
**Planning input:** owner-held private 2027 financial planning workbook (never committed or copied)

## Purpose

Shift RHEN from an intraday-first presentation into one trustworthy capital intelligence product with **two non-competing horizons**:

- **Strategic (months/years):** fundamental company research, semiconductor and power supply chains, biological/neuromorphic/photonic computing, fusion/fission/microreactors, research milestones, capital-plan constraints and quarterly thesis reviews.
- **Active (minutes/days):** preserve existing deterministic scanners, research/replay and broker safety as an isolated, independently authorized lane. No strategy rewriting or implied profitable alpha.

No new GRAEN/NOSTRA/VELUM standalone deployments. GRAEN's research, VELUM's replay and NOSTRA's optional forecast become internal RHEN features per owner-locked architecture. Do not make IREN, a model API, or a GPU a dependency of protected finance or orders.

## Experience: RHEN Continuance Terminal

1. **Overview / Capital Observatory:** read-only verified vs unverified status, financial readiness, as-of dates, quarter objectives; never display invented cash or performance.
2. **Sector Atlas:** thematic map, company research registry, dependencies, public/private distinctions, energy-to-compute links, first/second-order beneficiaries.
3. **Thesis Lab:** falsifiable thesis, dated source links, catalysts, failure conditions, evidence status, review cadence. A source link is not an independently verified claim.
4. **Portfolio Lens:** Alpaca positions only after separately authorized read-only connection; user-entered snapshots are labeled *declared, unverified*. Separate household, ANEVUM operating assets and portfolio; ETF constituent look-through is as-of dated, with unclassified weight explicitly retained.
5. **Capital Gateway:** consumes a future **redacted, signed** owner-authorized planning decision from the separate household/ANEVUM financial system. It is not a bank connector, funds-transfer tool, trading approval, debt manager or discretionary money allocator.
6. **Replay and Research:** on-demand pure analysis, regime/event studies, stress scenarios, source completeness and out-of-sample protocols; no automatic strategy promotion.
7. **Execution:** retain Alpaca adapter and only independently approved paper/limited live modes; no financial plan, thesis score or optional AI model can grant brokerage authority.

### Visual language

A midnight-navy Continuance Institute observatory, restrained gold and cold-blue astronomical plotting, orbital sector navigation and animated dependency lines where useful. Dense figures must remain readable; honor reduced-motion, keyboard support, mobile safe areas and source/timestamp disclosures. Motion is orientation, never evidence. A prototype is synthetic and must not be placed on a live authenticated origin without review.

## Strategic universe / ontology

Research topics are **not** a buy list. Initial categories:

- Semiconductors: design, foundries, fabrication tools, advanced packaging, HBM/memory, power semiconductors, photonic interconnects.
- Future computing: neuromorphic processors, biological systems; distinguish demonstrated prototypes from commercial clusters.
- Energy: grid/cooling infrastructure, fission, fusion, geothermal, storage, nuclear microwatt batteries, megawatt-class *microreactors*.

Do not conflate betavoltaic/diamond microwatt devices with microreactors that can generate industrial electricity. Research entities may be private or institutions with **no tradeable ticker**. A public company may participate in multiple themes, but monetary portfolio attribution must split exposure into an exclusive 100% or smaller look-through distribution to avoid artificial double counting.

## Governance and ownership boundaries

- **Household:** private cash, essentials, debt, taxes, subscriptions, family reserves and signoff remain outside RHEN. Never upload the private financial workbook to this public repository or expose family data to member research.
- **ANEVUM business:** separate ledger, operating liabilities, taxes and continuity runway remain independently authoritative. RHEN cannot move, pledge, or sweep business capital.
- **Alpaca:** active broker. Credentials, account balances, actual positions, orders and fills are broker-authoritative **only after authentic tenant-scoped read-only adapter verification**. Do not substitute IBKR or infer balances from prices and research.
- **RHEN:** read-only market research by default; isolated paper execution later. A thesis or portfolio projection can never call execution by itself.
- **Approval:** owner-directed plan changes, deposits, transfers, live trading, customer entitlements, strategy promotion and production deployment require separate authenticated gates and evidence.

## Existing workbook integration (future, read-only)

The private 2027 workbook has 22 tabs, including these relevant interfaces:

| Private workbook source | RHEN use | Boundary |
| --- | --- | --- |
| `2027 Setup` | Capital policy state, draft owner-selected allocation policy, reserve targets | Proposed targets only, *not* available funds or trading authority |
| `2027 Cash Flow` | Read-only monthly actuals/close signoff | No RHEN writes, no inferred eligibility if a month is incomplete |
| `2027 Quarterly`, `2027 Reviews` | Q1–Q4 milestones and performance reviews | Review receipts only; nothing schedules live trading |
| `2027 Portfolio`, `Alpaca Activity Log` | Declared holdings vs broker reconciliation | Never convert manual entries into verified Alpaca balances |
| `2027 Theme Split` | Draft thematic sleeve breakdown held in private finance records | No incremental allocation added to the existing thematic ceiling |
| `2027 Watchlist`, `2027 Semiconductors` | Candidate ideas for analyst-curated thesis register | Research only, not approved securities or recommendations |
| `2027 Source Notes` | Data provenance and outstanding gaps | Keep review dates and source URLs |

A later adapter may export a minimal, private, structured **policy-receipt** (date, hash, authorizing workspace, flags, maximum approved cap) only after identity, signature, staleness, origin and explicit privacy review. No raw account identifiers, private family transactions, card data, bank connections, PII or API secrets in public source or analytics logs.

**Under current unverified financial inputs, new-money investability is UNKNOWN / BLOCKED.** The owner's draft allocation policy is a planning draft, not an instruction to buy or a guarantee of available capital. Reserve targets are illustrative and editable and require actual expense reconciliation; high-APR debt/tax liabilities must be reviewed first.

## First additive code slice

`next_rhen/research/strategic_atlas.py` implements **only** two bounded, deterministic functions:

- `compile_strategic_atlas`: accepts canonical workspace-scoped research entries with precise sources, date, classification, hypothesis and disconfirmation; produces a digest-bound projection explicitly marked links-unverified and RESEARCH_ONLY. Refuses private companies with invented ticker symbols, unknown sectors, duplicate IDs, foreign records, future timestamps and extra credential-like fields.
- `summarize_declared_exposure`: computes supplied economic theme weights through ETF/direct-equity positions without duplicating position value; reports missing holdings/ETF look-through as unknown, not zero. Does not fetch Alpaca data or claim proof of ownership.

Both outputs contain `broker_order_authority=false`, `transfer_authority=false`, and have **no network, database, broker, execution, scheduling or AI dependencies**. Local Python tests cover identity, hostile fields, staleness, private-vs-public entities, false zero holdings, ETF attribution, overallocated weights, repeatability and unverified source disclosure.

This code is an internal research library on an unmerged successor branch, not a deployed website or brokerage feature. No authenticated RHEN UI route, customer-facing API, balance ingestion or scheduler is mounted by this patch.

## Release and implementation sequence

- **R0: this PR / isolated research contract.** Keep tests green and verify diff is additive against draft #490; exact-head CI must pass.
- **R1: verified research source adapters.** Curated dated research evidence, filing/earnings verification, lifecycle milestones, accurate symbol and listing-status registry. Track stale/retracted sources and avoid autonomous investment rankings.
- **R2: read-only portfolio.** Tenant-isolated Alpaca OAuth (once reviewed), broker reconciliation, ETF constituent coverage and source-date tests. No broad family finance connection.
- **R3: financial readiness.** Signed, scoped capital-policy receipt consumed from separately approved finance system. Missing, stale, unsigned, unreconciled or debt/reserve-blocked status => `RESEARCH_ONLY`. No order authorization.
- **R4: Continuance Terminal.** Private, authenticated, mobile-first views with synthetic preview before integration. Distinct founder and member workspaces; no raw fills, business cash or household records on public pages.
- **R5: paper strategy bridge.** Controlled paper-only thematic baskets and stress/replay using separately verifiable data, documented constraints, and explicit manual approval. Do not promote a paper result to validated alpha.
- **R6: release gates.** Source and security review, cross-tenant negative tests, OAuth revocation, backup/restore, budget/staleness incidents, realistic costs, owner approval, verified rollback. Future live capability requires an entirely separate explicit authorization.

## Not authorized by this redesign

No merge to RHEN `main`, no Railway or Cloudflare deployment/provisioning, no broker order or transfer, no login/roles change, no bank or household data ingestion, no API-model spend, no artificial trading performance, no claim that nuclear batteries can power GPUs at microwatt scale, no strategy-risk change, no public launch, and no new IREN/GRAEN/VELUM/NOSTRA service.