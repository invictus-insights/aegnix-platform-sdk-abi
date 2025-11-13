# AEGNIX ABI SDK

The **AEGNIX ABI SDK** provides the foundational components for managing secure swarm admission, keyring governance, policy enforcement, and signed audit logging within the AEGNIX ecosystem.

It serves as the backbone for the **Agent Bridge Interface (ABI)** — the layer that validates, authenticates, and authorizes Atomic Experts (AEs) to join and participate in the secure swarm communication mesh.

---

## Project Structure

```
aegnix_sdk/
├── aegnix_abi/
│   ├── __init__.py
│   ├── admission.py        # Handles dual-crypto handshake (AE registration)
│   ├── audit.py            # Writes signed audit events (file or Pub/Sub)
│   ├── keyring.py          # Manage public keys for AEs (add, list, revoke)
│   ├── policy.py           # Maps subjects to authorized publishers/subscribers
│   └── transport_pubsub.py # Adapter for publishing audit events via Pub/Sub
├── aegnix_ae/
│   └── (coming soon)       # AE SDK modules
└── tests/
    ├── test_abi_sdk.py     # End-to-end ABI SDK unit tests
    └── test_ae_sdk.py      # Placeholder for AE SDK tests
```

---

## Installation

1. **Ensure AEGNIX Core is installed locally:**

   ```bash
   cd ../aegnix_core
   pip install -e .
   ```

2. **Install the ABI SDK (editable mode):**

   ```bash
   cd ../aegnix_sdk
   pip install -e .
   ```

3. **Confirm successful installation:**

   ```bash
   pip list | grep aegnix
   ```

   You should see something like:

   ```
   aegnix-core 0.1.0
   aegnix-sdk  0.1.0
   ```

---



## Core Concepts

| Module        | Responsibility                                                                    |
| ------------- | --------------------------------------------------------------------------------- |
| **Keyring**   | Manage trusted AE keys (CRUD). Stored in SQLite by default.                       |
| **Admission** | Handles the `who_is_there` dual-crypto handshake. Issues and verifies challenges. |
| **Policy**    | Defines which subjects each AE can publish or subscribe to.                       |
| **Audit**     | Writes signed audit envelopes to disk or a Pub/Sub topic.                         |
| **Transport** | Adapter abstraction layer for different pub/sub backends (GCP, Kafka, NATS).      |

---

## Running Tests

You can run the full ABI SDK test suite with detailed debug logs:

```bash
pytest -v -s --log-cli-level=DEBUG tests/test_abi_sdk.py

```

Expected output:

```
================================================================ test session starts ================================================================
platform win32 -- Python 3.11.x, pytest-8.x.x
rootdir: E:\git\invictus_insights\platform\aegnix_sdk
testpaths: tests
collected 4 items

tests/test_abi_sdk.py ....                                                                                                    [100%]

================================================================ 5 passed in 0.35s ================================================================
```

---

## Current Milestone: Phase 3E (v0.3.6)

All core ABI SDK modules stable:
* [x] Dual-crypto admission handshake (`Signature valid`)
* [x] Keyring + PolicyEngine verified
* [x] AuditLogger file-based logging
* [x] Full test suite passing (5/5)


---

## Definition of Done (Phase 3E)
* [x] Keyring CRUD operations
* [x] Dual-crypto admission handshake (Signature valid)
* [x] Policy enforcement rules
* [x] Signed audit logging
* [x] Full unit test coverage
* [ ] JWT token grants + `/emit` verification (Phase 3F)

---

## Next Steps

Next: JWT issuance and verification (Phase 3F)

---

### ABI ↔ AE SDK Integration
The ABI SDK now communicates with the **ABI Service** through the admission handshake and will integrate with its `/emit` and `/subscribe` endpoints in Phase 3F.

This ensures consistent trust validation across AE client libraries and backend services.

## Quick Example
```python
from aegnix_abi.keyring import ABIKeyring
from aegnix_abi.admission import AdmissionService

keyring = ABIKeyring("db/abi_state.db")
svc = AdmissionService(keyring)
nonce = svc.issue_challenge("fusion_ae")
```



**Author:** Invictus Insights R&D  
**Version:** 0.3.6 (Phase 3E All Green)  
**License:** Proprietary / Pending Patent Filing
