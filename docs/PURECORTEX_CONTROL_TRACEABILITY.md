# PURECORTEX Control-to-Code Traceability

This matrix maps benchmark control families to concrete PURECORTEX implementation files and current test coverage status.

## Legend

- `Covered`: control has explicit code guard plus direct test evidence.
- `Partial`: code guard exists but tests are incomplete for adversarial paths.
- `Gap`: missing or weak direct evidence for the control.

## Traceability Matrix

| Control Family | Code Paths | Current Tests | Status | Gap Notes |
|---|---|---|---|---|
| Authorization and caller binding | `contracts/smart_contracts/governance/contract.py`, `contracts/smart_contracts/creator_vesting/contract.py`, `backend/src/api/auth.py` | `contracts/tests/test_governance_contract.py`, `contracts/tests/test_creator_vesting.py`, `backend/tests/test_auth_bootstrap.py` | Partial | Contract tests currently emphasize state/math; sender/authz transaction-path tests need expansion. |
| Transaction structure and input validation | `contracts/smart_contracts/governance/contract.py`, `contracts/smart_contracts/agent_factory/contract.py`, `scripts/deploy_mainnet.py` | `contracts/tests/test_agent_factory.py` | Partial | Governance `cast_vote` and reclaim flows need stronger abuse-case coverage. |
| Arithmetic/rounding/overflow safety | `contracts/smart_contracts/agent_factory/contract.py`, `contracts/smart_contracts/governance/contract.py`, `contracts/smart_contracts/creator_vesting/contract.py` | `contracts/tests/test_agent_factory.py`, `contracts/tests/test_creator_vesting.py` | Partial | Additional edge vectors needed for proposal quorum/supermajority and vesting claim lifecycle. |
| State isolation and box-key safety | `contracts/smart_contracts/agent_factory/contract.py`, `contracts/smart_contracts/governance/contract.py` | `contracts/tests/test_agent_factory.py`, `contracts/tests/test_governance_contract.py` | Partial | Cross-namespace collision and reclaim/delete anti-replay testing is still sparse. |
| Governance integrity and anti-replay | `contracts/smart_contracts/governance/contract.py` | `contracts/tests/test_governance_contract.py`, `backend/tests/test_governance_voting.py` | Partial | Need explicit vote lifecycle tests for snapshot params and reclaim replay prevention. |
| Backend auth fail-closed | `backend/src/api/auth.py`, `backend/main.py` | `backend/tests/test_auth_bootstrap.py`, `backend/tests/test_request_ip.py`, `backend/tests/test_developer_access_api.py` | Partial | Missing focused middleware matrix and websocket session lifecycle security tests. |
| Signer isolation and secret hygiene | `backend/src/services/signing_vault.py`, `backend/src/services/signer_daemon.py`, `backend/src/services/signer_client.py` | `backend/tests/test_signing_vault_security.py`, `backend/tests/test_signer_daemon.py` | Covered | Keep regression checks as signer/auth code evolves. |
| Prompt injection and consensus safety | `backend/orchestrator.py`, `backend/sandboxing.py`, `backend/src/agents/base_agent.py` | none dedicated | Gap | No dedicated orchestrator security tests yet for `<user_query>` wrapping and fail-closed consensus branches. |
| Airdrop Merkle proof correctness | `scripts/airdrop_snapshot.py` | `scripts/test_airdrop_snapshot.py` | Gap | Current tests validate root/leaf properties but not proof generation/verification end-to-end. |

## Priority Gap Backlog (Execution Order)

1. Add orchestrator security tests (`backend/tests/test_orchestrator_security.py`).
2. Expand backend auth/ws tests (`backend/tests/test_auth_middleware_security.py`, `backend/tests/test_websocket_auth_security.py`).
3. Expand governance and vesting adversarial transaction-path tests.
4. Add Merkle proof verification tests in `scripts/test_airdrop_snapshot.py`.
