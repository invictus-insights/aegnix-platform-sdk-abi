"""
ABI SDK — Audit Logger
Writes signed audit events locally or to a message bus.
"""

import json
from aegnix_core.envelope import Envelope
from aegnix_core.crypto import sign_envelope
from aegnix_core.utils import now_ts

class AuditLogger:
    def __init__(self, priv_key=None, key_id="abi-ed25519-1", file_path="abi_audit.log", transport=None):
        self.priv_key = priv_key
        self.key_id = key_id
        self.file_path = file_path
        self.transport = transport  # optional Pub/Sub adapter

    def log_event(self, event_type, payload):
        env = Envelope(producer="abi-service", subject=f"audit.{event_type}", payload=payload)
        if self.priv_key:
            sign_envelope(env, self.priv_key, self.key_id)
        entry = json.dumps(env.to_dict(), separators=(",", ":"), sort_keys=True)
        with open(self.file_path, "a") as f:
            f.write(entry + "\n")
        if self.transport:
            self.transport.publish("abi.audit.events", entry.encode())
