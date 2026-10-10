# Security Policy

## Supported scope

Security maintenance is prioritized for the current production path on `main` and for separately reviewed V5 successor work. Historical branches and archived experiments are not necessarily maintained. A public draft PR or passing CI is not a deployed security fix.

## Report vulnerabilities privately

Do **not** post an exploit, leaked credential, account data, authentication weakness, trading-control bypass, member isolation flaw, or other sensitive finding in a public issue or pull request.

Email **devon@anevum.com** with a concise description, affected file/route and version, potential impact, reproduction steps, and redacted evidence. If GitHub private vulnerability reporting is enabled for this repository, it may also be used. Do not assume an immediate response or public bounty.

Do not include real Alpaca credentials, order/position/account details, token values, private logs or member identities in reports sent through public systems.

## Research boundaries

- Do not trade, modify brokerage accounts, attempt order placement, bypass authorization, or request credentials as part of security research.
- Do not probe production endpoints, exfiltrate data, perform denial of service, social-engineer users, or access records you do not own.
- Use local synthetic test data whenever possible. If you encounter real sensitive data, stop and use private reporting.
- Repository visibility is not permission to operate RHEN, inspect brokerage accounts, or test users' terminals.

## Trust boundaries

Protected live execution, operational controls, broker tokens, runtime data, account separation, and private evidence are not public services. Research/replay pipelines cannot themselves authorize strategy promotion or broker writes. Security claims should distinguish locally tested draft code from currently deployed paths.

ANEVUM does not currently announce a public bug bounty or guaranteed response SLA in this repository.
