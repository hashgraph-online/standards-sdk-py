# HOL HCS SDK (Python)

[![PyPI Version](https://img.shields.io/pypi/v/standards_sdk_py?logo=pypi&logoColor=white)](https://pypi.org/project/standards-sdk-py/)
[![Python Versions](https://img.shields.io/pypi/pyversions/standards_sdk_py)](https://pypi.org/project/standards-sdk-py/)
[![PyPI Downloads](https://img.shields.io/badge/PyPI%20downloads-tracking%20pending-lightgrey)](https://pypi.org/project/standards-sdk-py/)
[![CI](https://github.com/hashgraph-online/standards-sdk-py/actions/workflows/ci.yml/badge.svg)](https://github.com/hashgraph-online/standards-sdk-py/actions/workflows/ci.yml)
[![Security](https://github.com/hashgraph-online/standards-sdk-py/actions/workflows/security.yml/badge.svg)](https://github.com/hashgraph-online/standards-sdk-py/actions/workflows/security.yml)
[![CodeQL](https://github.com/hashgraph-online/standards-sdk-py/actions/workflows/codeql.yml/badge.svg)](https://github.com/hashgraph-online/standards-sdk-py/actions/workflows/codeql.yml)
[![Publish](https://github.com/hashgraph-online/standards-sdk-py/actions/workflows/publish.yml/badge.svg)](https://github.com/hashgraph-online/standards-sdk-py/actions/workflows/publish.yml)
[![License](https://img.shields.io/github/license/hashgraph-online/standards-sdk-py)](./LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/hashgraph-online/standards-sdk-py?style=social)](https://github.com/hashgraph-online/standards-sdk-py/stargazers)
[![CodeSandbox Examples](https://img.shields.io/badge/CodeSandbox-Examples-151515?logo=codesandbox&logoColor=white)](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples)
[![Typing: mypy](https://img.shields.io/badge/typing-mypy-blue.svg)](https://mypy.readthedocs.io/)
[![Code Style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Lint: ruff](https://img.shields.io/badge/lint-ruff-D7FF64.svg)](https://github.com/astral-sh/ruff)
[![HOL SDK Docs](https://img.shields.io/badge/%F0%9F%93%9A_SDK_Docs-hol.org-4A90D9)](https://hol.org/docs/libraries/standards-sdk/)
[![HCS Standards](https://img.shields.io/badge/%F0%9F%93%96_HCS_Standards-hol.org-8B5CF6)](https://hol.org/docs/standards)

| ![](./Hashgraph-Online.png) | Python reference implementation of the Hiero Consensus Specifications (HCS) and Registry Broker utilities with parity against the TypeScript and Go SDKs.<br><br>[📚 Standards SDK Documentation](https://hol.org/docs/libraries/standards-sdk/)<br>[📖 Hiero Consensus Specifications Documentation](https://hol.org/docs/standards) |
| :-------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

## Quick Start

```bash
cd standards-sdk-py
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Install

```bash
pip install standards-sdk-py
```

## Developer Tooling

```bash
cd standards-sdk-py
.venv/bin/pre-commit install
.venv/bin/pre-commit run --all-files
```

## Documentation

For standards and API documentation:

- [Standards SDK Documentation](https://hol.org/docs/libraries/standards-sdk/)
- [HCS Standards Documentation](https://hol.org/docs/standards)

## Supported Packages

| Package | Coverage |
| :--- | :--- |
| `standards_sdk_py.hcs2` | HCS-2 registry topic creation, indexed entry operations, memo helpers, mirror reads. |
| `standards_sdk_py.hcs3` | HCS-3 recursive file loading helpers. |
| `standards_sdk_py.hcs5` | HCS-5 hashinal inscription and minting helpers. |
| `standards_sdk_py.hcs6` | HCS-6 non-indexed registry creation, registration helpers, memo helpers. |
| `standards_sdk_py.hcs7` | HCS-7 indexed registry and metadata registration helpers. |
| `standards_sdk_py.hcs10` | HCS-10 topic/message builders and communication helpers. |
| `standards_sdk_py.hcs11` | HCS-11 profile models/builders, validation, inscription helpers. |
| `standards_sdk_py.hcs12` | HCS-12 action/assembly/hashlinks helpers. |
| `standards_sdk_py.hcs14` | HCS-14 UAID parsing and resolution helpers. |
| `standards_sdk_py.hcs15` | HCS-15 account creation and memo helpers. |
| `standards_sdk_py.hcs16` | HCS-16 flora account/topic/message helpers. |
| `standards_sdk_py.hcs17` | HCS-17 state-hash helpers. |
| `standards_sdk_py.hcs18` | HCS-18 discovery topic/message helpers. |
| `standards_sdk_py.hcs20` | HCS-20 points message and validation helpers. |
| `standards_sdk_py.hcs21` | HCS-21 adapter declaration helpers. |
| `standards_sdk_py.hcs26` | HCS-26 memo parser/resolver helpers. |
| `standards_sdk_py.hcs27` | HCS-27 checkpoint helpers. |
| `standards_sdk_py.inscriber` | Inscriber auth, quote, submit, and polling workflows. |
| `standards_sdk_py.registry_broker` | Full Registry Broker client (search, adapters, registries, credits, verification, chat/encryption, skills, ledger auth). |
| `standards_sdk_py.mirror` | Mirror node client used by standards and inscriber modules. |
| `standards_sdk_py.shared` | transport, config, network/operator helpers, and shared typing. |

## CodeSandbox Examples

- [Examples index](./examples/README.md)
- [standards-sdk-discovery](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/standards-sdk-discovery)
- [hcs2-create-registry](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs2-create-registry)
- [hcs5-build-mint](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs5-build-mint)
- [hcs6-create-registry](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs6-create-registry)
- [hcs7-register-metadata](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs7-register-metadata)
- [hcs10-build-message](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs10-build-message)
- [hcs11-build-agent-profile](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs11-build-agent-profile)
- [hcs12-build-register](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs12-build-register)
- [hcs14-parse-uaid](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs14-parse-uaid)
- [hcs15-build-account-tx](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs15-build-account-tx)
- [hcs16-build-flora-topic-tx](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs16-build-flora-topic-tx)
- [hcs17-build-state-message](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs17-build-state-message)
- [hcs18-build-announce](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs18-build-announce)
- [hcs20-deploy-points](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs20-deploy-points)
- [hcs21-build-declaration](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs21-build-declaration)
- [hcs26-parse-memos](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs26-parse-memos)
- [hcs27-publish-checkpoint](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs27-publish-checkpoint)
- [inscriber-auth-client](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/inscriber-auth-client)
- [mirror-topic-messages](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/mirror-topic-messages)
- [registry-broker-skill-domain-proof](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/registry-broker-skill-domain-proof)
- [registry-broker-uaid-dns-verification](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/registry-broker-uaid-dns-verification)

## Environment Variables

Common:

- `HEDERA_NETWORK`
- `HEDERA_ACCOUNT_ID` or `HEDERA_OPERATOR_ID`
- `HEDERA_PRIVATE_KEY` or `HEDERA_OPERATOR_KEY`

Network-scoped overrides:

- `TESTNET_HEDERA_ACCOUNT_ID`
- `TESTNET_HEDERA_PRIVATE_KEY`
- `MAINNET_HEDERA_ACCOUNT_ID`
- `MAINNET_HEDERA_PRIVATE_KEY`

Registry Broker:

- `REGISTRY_BROKER_BASE_URL`
- `REGISTRY_BROKER_API_KEY`
- `REGISTRY_BROKER_LEDGER_API_KEY`

Inscriber integration:

- `RUN_INTEGRATION=1`
- `RUN_INSCRIBER_INTEGRATION=1`

## Tests

Unit and contract tests:

```bash
cd standards-sdk-py
.venv/bin/pytest -q
```

Parity checks:

```bash
cd standards-sdk-py
.venv/bin/standards-sdk-py-generate-inventory --repo-root ..
.venv/bin/standards-sdk-py-check-parity
```

Live testnet inscriber end-to-end:

```bash
cd standards-sdk-py
cp ../standards-sdk/.env ./.env
pip install hedera-sdk-py
set -a
source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' ./.env)
set +a
export RUN_INTEGRATION=1
export RUN_INSCRIBER_INTEGRATION=1
.venv/bin/pytest -m integration -k inscriber_registry_broker_end_to_end_testnet -vv -rs
```

Live testnet HCS-2 end-to-end:

```bash
cd standards-sdk-py
export RUN_INTEGRATION=1
export RUN_HCS2_INTEGRATION=1
export HEDERA_NETWORK=testnet
export TESTNET_HEDERA_ACCOUNT_ID="<your-testnet-account-id>"
export TESTNET_HEDERA_PRIVATE_KEY="<your-testnet-private-key>"
.venv/bin/pytest -m integration -k hcs2_end_to_end_testnet -vv -rs
```

Notes:

- Set `HEDERA_NETWORK=testnet` (and do not set a conflicting `INSCRIBER_HEDERA_NETWORK`).
- The test uses ledger challenge auth from your testnet credentials to avoid accidentally using a mainnet-scoped API key.

## CI/CD and Security

- Python matrix CI (`3.11`, `3.12`, `3.13`) for `ruff`, `black`, `mypy`, unit tests, parity checks, and package validation.
- Security workflows for dependency review, `pip-audit`, Bandit SARIF upload, CodeQL, and verified TruffleHog secret scanning.
- Release workflow for build + `twine check`, TestPyPI/PyPI trusted publishing, checksum artifacts, provenance attestations, and GitHub release notes.

## Contributing

Open issues or pull requests in the repository:

- <https://github.com/hashgraph-online/standards-sdk-py/issues>

## Security

For disclosure and response policy, see [SECURITY.md](./SECURITY.md).

## Maintainers

Maintained by Hashgraph Online.

## Resources

- [Hiero Consensus Specifications (HCS) Documentation](https://hol.org/docs/standards)
- [Hedera Documentation](https://docs.hedera.com)
- [Telegram Community](https://t.me/hashinals)

## License

MIT
