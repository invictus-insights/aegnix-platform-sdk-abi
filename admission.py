"""
ABI SDK — Admission Service
Implements the dual-crypto “Who’s There?” handshake.
"""

import os, base64
from aegnix_core.crypto import ed25519_verify, x25519_generate, derive_key
from aegnix_core.utils import b64e, b64d, now_ts
from aegnix_core.envelope import Envelope

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
        """
        rec = self.keyring.get_key(ae_id)
        if not rec or rec.status != "trusted":
            return False, "untrusted"

        challenge = self.active_challenges.get(ae_id)
        if not challenge:
            return False, "no_active_challenge"

        nonce = challenge["nonce"]

        # --- Safe base64 decoding for key and signature ---
        def safe_b64decode(data: str) -> bytes:
            """Decode base64 safely even if missing padding."""
            data = data.strip()
            padding_needed = 4 - (len(data) % 4)
            if padding_needed and padding_needed != 4:
                data += "=" * padding_needed
            return base64.b64decode(data)

        try:
            pub_raw = safe_b64decode(rec.pubkey_b64)
            sig_bytes = safe_b64decode(signed_nonce_b64)
        except Exception as e:
            return False, f"decode_error: {e}"

        # --- Verify signature ---
        try:
            valid = ed25519_verify(pub_raw, sig_bytes, nonce)
            if valid:
                # Clean up challenge after success
                del self.active_challenges[ae_id]
                return True, "Signature valid"
            else:
                return False, "Invalid signature"
        except Exception as e:
            return False, f"Verification error: {e}"

    # def verify_response(self, ae_id: str, signed_nonce_b64: str):
    #     """
    #     Validate AE-signed challenge using canonical Ed25519 order.
    #
    #     Verifies:
    #         ed25519_verify(pub_raw, sig_bytes, nonce_bytes)
    #     """
    #     rec = self.keyring.get_key(ae_id)
    #     if not rec or rec.status != "trusted":
    #         return False, "untrusted"
    #
    #     challenge = self.active_challenges.get(ae_id)
    #     if not challenge:
    #         return False, "no_active_challenge"
    #
    #     nonce = challenge["nonce"]
    #     pub_raw = base64.b64decode(rec.pubkey_b64)
    #     sig_bytes = base64.b64decode(signed_nonce_b64)
    #
    #     try:
    #         # Canonical order: (pub_raw, sig, data)
    #         valid = ed25519_verify(pub_raw, sig_bytes, nonce)
    #         if valid:
    #             del self.active_challenges[ae_id]
    #             return True, "Signature valid"
    #         else:
    #             return False, "Invalid signature"
    #     except Exception as e:
    #         return False, f"Verification error: {e}"
    #
