"""
ABI SDK — Keyring Management
Manages AE public keys, trust state, and rotations.
"""
from aegnix_core.crypto import compute_pubkey_fingerprint
from aegnix_core.storage import SQLiteStorage, KeyRecord
from aegnix_core.utils import now_ts



class ABIKeyring:
    def __init__(self, store):
        self.store = store
# class ABIKeyring:
#     def __init__(self, db_path="abi_state.db"):
#         self.store = SQLiteStorage(db_path)

    def add_key(self, ae_id: str, pubkey_b64: str, roles: str = "", status: str = "untrusted", expires_at=None):
        """
        Add or update an AE public key in the keyring.

        Args:
            ae_id (str):
                Unique identifier for the Atomic Expert.
            pubkey_b64 (str):
                Base64-encoded Ed25519 public key.
            roles (str, optional):
                Comma-separated role labels (e.g. "producer,analytics").
            status (str, optional):
                Trust state for the identity ("trusted", "untrusted", "pending").
                Defaults to "untrusted".
            expires_at (int, optional):
                Optional expiration timestamp for the key.

        Automatically Computes:
            pub_key_fpr (str):
                Stable fingerprint derived from the public key for identity binding.

        Returns:
            KeyRecord:
                The stored keyring record.
        """
        pub_key_fpr = compute_pubkey_fingerprint(pubkey_b64)

        rec = KeyRecord(ae_id=ae_id,
                        pubkey_b64=pubkey_b64,
                        roles=roles,
                        status=status,
                        expires_at=expires_at,
                        pub_key_fpr=pub_key_fpr)
        self.store.upsert_key(rec)
        self.store.log_event("key_added", {"ae_id": ae_id, "status": status, "ts": now_ts()})
        return rec

    def revoke_key(self, ae_id: str):
        self.store.revoke_key(ae_id)
        self.store.log_event("key_revoked", {"ae_id": ae_id, "ts": now_ts()})

    def get_by_aeid(self, ae_id: str):
        """Return the key record for a given AE ID."""
        return self.store.get_key(ae_id)

    def get_by_fpr(self, pub_key_fpr: str):
        """Return key record by fingerprint (pub_key_fpr)."""
        cur = self.store.db.execute(
            "SELECT ae_id, pubkey_b64, roles, status, expires_at, pub_key_fpr "
            "FROM keyring WHERE pub_key_fpr = ?",
            (pub_key_fpr,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return KeyRecord(*row)

    def get_by_pubkey(self, pubkey_b64: str):
        """Return key record by exact public key (rarely used)."""
        cur = self.store.db.execute(
            "SELECT ae_id, pubkey_b64, roles, status, expires_at, pub_key_fpr "
            "FROM keyring WHERE pubkey_b64 = ?",
            (pubkey_b64,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return KeyRecord(*row)

    def get_key(self, ae_id: str):
        return self.store.get_key(ae_id)

    def list_keys(self):
        cur = self.store.db.execute("SELECT ae_id, pubkey_b64, roles, status, expires_at FROM keyring")
        return [dict(zip(["ae_id", "pubkey_b64", "roles", "status", "expires_at"], row)) for row in cur.fetchall()]

    # trust elevation from ABI side only
    def set_trusted(self, ae_id: str) -> bool:
        rec = self.store.get_key(ae_id)
        if not rec:
            return False
        if rec.status == "trusted":
            return True  # idempotent

        rec.status = "trusted"
        self.store.upsert_key(rec)
        self.store.log_event("key_trusted", {"ae_id": ae_id, "ts": now_ts()})
        return True

    def set_roles(self, ae_id: str, roles: str) -> None:
        """
        Update roles for an AE identity.

        Notes:
            - roles is a simple comma-separated string (e.g. "producer,analytics")
            - Keyring is the single source of truth for roles.
            - Uses SQLiteStorage under self.store
        """
        cur = self.store.db.cursor()
        cur.execute(
            "UPDATE keyring SET roles = ? WHERE ae_id = ?",
            (roles, ae_id)
        )
        self.store.db.commit()

        # Optional audit line (consistent with keyring behavior)
        self.store.log_event("key_roles_updated", {
            "ae_id": ae_id,
            "roles": roles,
            "ts": now_ts()
        })