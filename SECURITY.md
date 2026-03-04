# Security Policy

## Supported Versions

Security fixes are provided for actively maintained releases.

| Version | Supported |
| ------- | --------- |
| `0.x`   | Yes       |
| `<0.1`  | No        |

## Reporting a Vulnerability

Do not open public GitHub issues for security vulnerabilities.

Use one of the following:

- GitHub Security Advisories for `hashgraph-online/standards-sdk-py`
- Email: `security@hashgraphonline.com`

Include:

- affected version
- reproduction steps
- proof-of-concept or stack trace
- impact assessment

You will receive acknowledgement within 3 business days. We aim to provide remediation guidance or a patch timeline within 7 business days.

## Security Practices

This project runs automated security checks in CI:

- dependency review on pull requests
- `pip-audit` for Python dependency CVEs
- `bandit` static analysis for Python code
- CodeQL analysis for Python
- secret scanning with TruffleHog

Release artifacts are built in CI, published via trusted publishing, and accompanied by provenance attestations.
