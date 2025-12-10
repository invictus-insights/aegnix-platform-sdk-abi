# aegnix_abi/admission.py

"""
ABI SDK — Admission Service
Implements the dual-crypto “Who’s There?” handshake.
"""
import os
from aegnix_core.crypto import ed25519_verify
from aegnix_core.utils import b64e, now_ts, b64d


class AdmissionService:
    def __init__(self, keyring, challenge_ttl=300):
        self.keyring = keyring
        self.challenge_ttl = challenge_ttl
        self.active_challenges = {}  # {ae_id: {"nonce":..., "ts":...}}

    def issue_challenge(self, ae_id: str):
        nonce = os.urandom(16)
        self.active_challenges[ae_id] = {"nonce": nonce, "ts": now_ts()}
        return b64e(nonce)

    def verify_response(self, ae_id: str, signed_nonce_b64: str):
        """
        Validate AE-signed challenge using canonical Ed25519 order.

        Verifies:
            ed25519_verify(pub_raw, sig_bytes, nonce_bytes)

        Behavior (3G):
            - AE must exist and not be revoked.
            - If signature is valid:
                * mark AE as trusted
                * clear challenge
        """
        rec = self.keyring.get_key(ae_id)
        if not rec:
            return False, "unknown_ae"
        if rec.status == "revoked":
            return False, "revoked"

        challenge = self.active_challenges.get(ae_id)
        if not challenge:
            return False, "no_active_challenge"

        nonce = challenge["nonce"]

        # --- Safe base64 decoding for key and signature ---
        def safe_b64decode(data: str) -> bytes:
            data = data.strip()
            padding_needed = 4 - (len(data) % 4)
            if padding_needed and padding_needed != 4:
                data += "=" * padding_needed
            return b64d(data)

        try:
            pub_raw = b64d(rec.pubkey_b64)
            sig_bytes = b64d(signed_nonce_b64)
        except Exception as e:
            return False, f"decode_error: {e}"

        # --- Verify signature ---
        try:
            valid = ed25519_verify(pub_raw, sig_bytes, nonce)
            if valid:
                # trust AE automatically on proof of private key
                self.keyring.set_trusted(ae_id)
                # Clean up challenge after success
                del self.active_challenges[ae_id]
                return True, "Signature valid"
            else:
                return False, "Invalid signature"
        except Exception as e:
            return False, f"Verification error: {e}"

