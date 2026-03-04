# Examples

Runnable examples for common [HOL Standards SDK](https://hol.org/docs/libraries/standards-sdk/)
flows. Each example maps to a supported HCS module or Registry Broker workflow.

| Example | Specification | Description |
| ------- | ------------- | ----------- |
| `standards-sdk-discovery` | SDK Core | Registry Broker discovery (`search`, `stats`, `list_protocols`) |
| `hcs2-create-registry` | [HCS-2](https://hol.org/docs/standards/hcs-2) | Builds typed HCS-2 registry + message payloads |
| `hcs5-build-mint` | [HCS-5](https://hol.org/docs/standards/hcs-5) | Builds HCS-5 mint/hashinal payloads |
| `hcs6-create-registry` | [HCS-6](https://hol.org/docs/standards/hcs-6) | Builds typed HCS-6 registry + register payloads |
| `hcs7-register-metadata` | [HCS-7](https://hol.org/docs/standards/hcs-7) | Builds HCS-7 config + metadata registration payloads |
| `hcs10-build-message` | [HCS-10](https://hol.org/docs/standards/hcs-10) | Sends a mocked HCS-10 `sendMessage` call |
| `hcs11-build-agent-profile` | [HCS-11](https://hol.org/docs/standards/hcs-11) | Builds + validates a mocked HCS-11 agent profile |
| `hcs12-build-register` | [HCS-12](https://hol.org/docs/standards/hcs-12) | Sends a mocked HCS-12 register action payload |
| `hcs14-parse-uaid` | [HCS-14](https://hol.org/docs/standards/hcs-14) | Parses UAID/DID payloads via mocked HCS-14 operations |
| `hcs15-build-account-tx` | [HCS-15](https://hol.org/docs/standards/hcs-15) | Builds typed HCS-15 account creation options |
| `hcs16-build-flora-topic-tx` | [HCS-16](https://hol.org/docs/standards/hcs-16) | Parses HCS-16 topic memo + builds flora topic options |
| `hcs17-build-state-message` | [HCS-17](https://hol.org/docs/standards/hcs-17) | Builds typed HCS-17 state-hash payloads |
| `hcs18-build-announce` | [HCS-18](https://hol.org/docs/standards/hcs-18) | Builds HCS-18 discovery announce payload |
| `hcs20-deploy-points` | [HCS-20](https://hol.org/docs/standards/hcs-20) | Builds typed HCS-20 points deployment payloads |
| `hcs21-build-declaration` | [HCS-21](https://hol.org/docs/standards/hcs-21) | Builds typed HCS-21 adapter declaration payloads |
| `hcs26-parse-memos` | [HCS-26](https://hol.org/docs/standards/hcs-26) | Builds + parses mocked HCS-26 topic/tx memos |
| `hcs27-publish-checkpoint` | [HCS-27](https://hol.org/docs/standards/hcs-27) | Builds mocked HCS-27 checkpoint + Merkle helpers |
| `inscriber-auth-client` | Inscriber | Builds typed quote request/options for inscription flows |
| `mirror-topic-messages` | Mirror Node | Reads mocked mirror topic messages and decoded payloads |
| `registry-broker-skill-domain-proof` | Registry Broker | Domain proof challenge + verify workflow (mocked) |
| `registry-broker-uaid-dns-verification` | Registry Broker | UAID DNS TXT verify + status workflow (mocked) |

## Run

```bash
cd standards-sdk-py
python -m venv .venv
source .venv/bin/activate
pip install -e .
python examples/hcs10-build-message/main.py
```

## CodeSandbox

- [`standards-sdk-discovery`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/standards-sdk-discovery)
- [`hcs2-create-registry`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs2-create-registry)
- [`hcs5-build-mint`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs5-build-mint)
- [`hcs6-create-registry`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs6-create-registry)
- [`hcs7-register-metadata`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs7-register-metadata)
- [`hcs10-build-message`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs10-build-message)
- [`hcs11-build-agent-profile`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs11-build-agent-profile)
- [`hcs12-build-register`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs12-build-register)
- [`hcs14-parse-uaid`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs14-parse-uaid)
- [`hcs15-build-account-tx`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs15-build-account-tx)
- [`hcs16-build-flora-topic-tx`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs16-build-flora-topic-tx)
- [`hcs17-build-state-message`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs17-build-state-message)
- [`hcs18-build-announce`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs18-build-announce)
- [`hcs20-deploy-points`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs20-deploy-points)
- [`hcs21-build-declaration`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs21-build-declaration)
- [`hcs26-parse-memos`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs26-parse-memos)
- [`hcs27-publish-checkpoint`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/hcs27-publish-checkpoint)
- [`inscriber-auth-client`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/inscriber-auth-client)
- [`mirror-topic-messages`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/mirror-topic-messages)
- [`registry-broker-skill-domain-proof`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/registry-broker-skill-domain-proof)
- [`registry-broker-uaid-dns-verification`](https://codesandbox.io/s/github/hashgraph-online/standards-sdk-py/tree/main/examples/registry-broker-uaid-dns-verification)

## Learn More

- [Standards SDK Documentation](https://hol.org/docs/libraries/standards-sdk/)
- [Hiero Consensus Specifications](https://hol.org/docs/standards)
- [Registry Broker](https://hol.org/registry)
- [Hashgraph Online](https://hol.org)
