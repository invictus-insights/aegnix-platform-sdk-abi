"""
ABI SDK — Keyring Management
Manages AE public keys, trust state, and rotations.
"""

from aegnix_core.storage import SQLiteStorage, KeyRecord
from aegnix_core.utils import now_ts

class ABIKeyring:
    def __init__(self, db_path="abi_state.db"):
        self.store = SQLiteStorage(db_path)

    def add_key(self, ae_id: str, pubkey_b64: str, roles: str = "", expires_at=None):
        rec = KeyRecord(ae_id=ae_id, pubkey_b64=pubkey_b64, roles=roles, expires_at=expires_at)
        self.store.upsert_key(rec)
        self.store.log_event("key_added", {"ae_id": ae_id, "ts": now_ts()})
        return rec

    def revoke_key(self, ae_id: str):
        self.store.revoke_key(ae_id)
        self.store.log_event("key_revoked", {"ae_id": ae_id, "ts": now_ts()})

    def get_key(self, ae_id: str):
        return self.store.get_key(ae_id)

    def list_keys(self):
        cur = self.store.db.execute("SELECT ae_id, pubkey_b64, roles, status, expires_at FROM keyring")
        return [dict(zip(["ae_id", "pubkey_b64", "roles", "status", "expires_at"], row)) for row in cur.fetchall()]
