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
        rec = self.keyring.get_key(ae_id)
        if not rec or rec.status != "trusted":
            return False, "untrusted"
        challenge = self.active_challenges.get(ae_id)
        if not challenge:
            return False, "no_active_challenge"
        nonce = challenge["nonce"]
        pubkey = base64.b64decode(rec.pubkey_b64)
        try:
            valid = ed25519_verify(pubkey, b64d(signed_nonce_b64), nonce)
            if valid:
                del self.active_challenges[ae_id]
                return True, "verified"
        except Exception as e:
            return False, str(e)
        return False, "invalid"
