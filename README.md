# AEGNIX ABI SDK (Phase 3F → 3G)

The **AEGNIX ABI SDK** is the developer-facing toolkit that allows **Atomic Experts (AEs)** to securely join, authenticate, publish, subscribe, and interact with the **AEGNIX Swarm Mesh**.

It implements:

* Dual‑crypto admission (nonce challenge + Ed25519 verification)
* Keyring trust synchronization
* JWT session authentication
* Verified & policy‑enforced emission
* Capability declaration (Phase 3G)
* The redesigned **PolicyContext** + policy evaluation engine
* Signed audit logging

This SDK is the **client half** of the ABI. The ABI Service is the authoritative enforcement layer; the ABI SDK is how AEs properly communicate with it.

---

# What’s New in Phase 3G

Phase 3G introduced the most significant update since Phase 3F:

### **New `PolicyContext`**

A strongly typed structure used by both ABI Service and ABI SDK to ensure consistent evaluation:

* `subjects`: static policy
* `ae_caps`: dynamic AE capabilities
* `resolved`: merged effective policy

### **Rewritten Policy Engine**

The ABI SDK now mirrors ABI Service policy logic:

* Deterministic merge of static + dynamic policy
* Backward‑compatibility shim for legacy static policies
* Unknown subject rejection
* Role‑aware subscription checks (future‑proofed)

### **Capability Declaration (Phase 3G)**

AEs can now declare their publishes/subscribes list via:

```python
client.set_capabilities({
  "publishes": ["fusion.topic"],
  "subscribes": ["roe.result"]
})
```

The JDWT is required and ABI Service syncs capabilities to SQLite.

### ✅ **Updated Test Suite Alignment**

The SDK now matches ABI Service behavior exactly across:

* Verified emission
* Signature validation
* Dynamic capability merging
* Authorization errors

---

# 📦 Project Structure

```
aegnix_sdk/
├── aegnix_abi/
│   ├── admission.py         # Nonce challenge & verification
│   ├── audit.py             # Signed audit envelopes
│   ├── keyring.py           # Local trusted AE keyring
│   ├── policy.py            # PolicyContext + merge engine
│   └── transport_pubsub.py  # Audit transport adapter
├── aegnix_ae/
│   ├── client.py            # Full AE client: register → JWT → emit
│   └── transport/           # HTTP, Local bus, Pub/Sub transports
└── tests/
    ├── test_abi_sdk.py      # ABI SDK policy & admission tests
    └── test_ae_sdk.py       # AE integration tests
```

---

# Installation

### 1. Install Core

```bash
cd ../aegnix_core
pip install -e .
```

### 2. Install ABI SDK

```bash
cd ../aegnix_sdk
pip install -e .
```

### 3. Verify

```bash
pip list | grep aegnix
```

Expected:

```
aegnix-core 0.3.x
aegnix-sdk  0.3.x
```

---

# Core Responsibilities of ABI SDK

| Component        | Purpose                                  |
| ---------------- | ---------------------------------------- |
| **admission.py** | Dual‑crypto verify + trust establishment |
| **keyring.py**   | Local trusted public key store           |
| **policy.py**    | Static+dynamic merged PolicyContext      |
| **audit.py**     | Signed audit events                      |
| **AE Client**    | Registration → JWT → Capabilities → Emit |

---

# Policy Engine Overview

The ABI SDK now uses the **same algorithm** as ABI Service.

### Static Policy

Loaded from ABI service via `/capabilities/effective`.

### Dynamic Capabilities

Provided via AE client declaration.

### Effective Policy

A deterministic merge:

```
resolved[subject] = union(static[subject], dynamic_caps)
```

### PolicyContext

```python
@dataclass
class PolicyContext:
    subjects: dict   # static
    ae_caps: list    # dynamic
    resolved: dict   # merged
```

---

# Example AE Registration + Emit

```python
from aegnix_ae.client import AEClient

client = AEClient(
    ae_id="fusion_ae",
    privkey_b64=privkey,
    abi_url="http://localhost:8000"
)

# 1. Register → nonce → verify
client.register()
client.verify()

# 2. Fetch JWT
client.refresh_jwt()

# 3. Declare capabilities
client.set_capabilities({
    "publishes": ["fusion.topic"],
    "subscribes": ["roe.result"]
})

# 4. Send a verified emission
resp = client.emit("fusion.topic", {"msg": "hello"})
print(resp)
```

---

# Tests

Run all tests:

```bash
pytest -v -s --log-cli-level=DEBUG
```

Expected:

```
7 passed, 0 failed
```

---

# 🗺 Roadmap

### Phase 3F (Done)

* Verified emission
* Admission flow
* Trusted keyring
* Signing + JWT alignment

### Phase 3G (Done)

* Capability declaration
* Dynamic policy merge
* PolicyContext engine
* Backward static policy compatibility
* SSE subscription gating

### Phase 4

* JWT refresh tokens
* Pub/Sub federation
* Key rotation

### Phase 5

* Federated ABI clusters
* Multi-domain trust bridging

---

**Author:** Invictus Insights R&D
**Version:** 0.3.8 (Phase 3 Complete)
**License:** Proprietary — Patent Pending
--