# Contributing to RHEN

RHEN is ANEVUM's market-research and deterministic execution codebase. Public visibility is intended to support inspection, methodological criticism, and carefully scoped collaboration. It does **not** grant order authority, data access, or permission to change any operating account.

**Licensing status:** RHEN has no root `LICENSE` at this checkpoint. Do not assume that public visibility is an open-source license or authorization to redistribute/commercialize the code. The owner must separately decide on license and contributor terms. The [ANEVUM public collaboration policy](https://github.com/anevum/anevum-web/blob/main/docs/ANEVUM_V5_PUBLIC_COLLABORATION_2026-10-10.md) is proposed in a separate documentation PR and may not yet be on web `main`.

## Useful public-safe work

- Documentation, architecture explanations and reproducibility improvements.
- Methodological critique with clearly distinguished development, validation, holdout, paper, and live results.
- Synthetic or explicitly public-safe test cases for research provenance, replay fidelity, and fail-closed behavior.
- Research questions with falsifiable hypotheses, data limitations, and no unsupported profitability claims.

GRAEN (research), VELUM (replay), NOSTRA (forecasting), and IREN (control) remain internal RHEN responsibilities; they are not separately released open-source products merely because their names appear in this repository.

## Not ordinary community changes

Broker order submission, live-trading parameters, execution arming, risk limits, strategy promotion, member account bindings, private data-plane operations, credentials, remote database/backup operations, deployment configuration, and changes that expand financial authority require explicit maintainer review outside the usual public issue flow. Draft V5 successor foundations are paper/research-only until approved; do not present draft tests as live execution readiness.

Never post credentials, account balances, positions, orders, fill records, strategy parameters protected by the public evidence contract, member data, or private incident artifacts. Historical commits can remain public even after a file is edited.

Report suspected security vulnerabilities privately via [SECURITY.md](SECURITY.md), not a public issue.

## Making a proposal

1. Check existing issues and [V5 RHEN draft #488](https://github.com/anevum/rhen/pull/488) so work does not duplicate an unmerged experiment.
2. State the observed problem, precise scope, expected behavior, and a synthetic reproduction or sanitized methodology.
3. Keep code patches bounded and include tests for logic changes. Do not run or request real broker transactions or live credentials to prove a patch.
4. Separate measured outcomes from assumptions; mark missing source observations and insufficient sample sizes honestly.
5. Explain possible impacts on source custody, replay, safety, authorization, cost, and mainline compatibility.

A contribution or PR review is not approval to merge, deploy, promote a strategy, use live capital, or broaden RHEN's authority. The maintainer retains those decisions.
