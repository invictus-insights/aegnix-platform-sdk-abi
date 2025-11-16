# aegnix_abi/policy.py

from __future__ import annotations
from typing import Dict, Set, List
import yaml

from aegnix_core.capabilities import AECapability


class PolicyEngine:
    """
    Phase 3G — Dynamic Policy Engine

    Combines:
      1. Static policy (config/policy.yaml) — HARD FENCE
      2. Dynamic AE capability declarations (SQLite)

    Dynamic requests are ONLY allowed if they fit inside static policy.
    """

    def __init__(self, static_policy: Dict = None, ae_caps: List[AECapability] = None):
        self.static_policy = static_policy or {}
        self.ae_caps = {c.ae_id: c for c in (ae_caps or [])}
        self.effective = self._build_effective_policy()

    # ----------------------------------------------------------------------
    # Build effective policy
    # ----------------------------------------------------------------------
    def _build_effective_policy(self) -> Dict:
        """
        Effective policy structure:

        {
          "subjects": {
            "fusion.topic": {
              "pubs": set([...]),
              "subs": set([...]),
              "labels": set([...])
            },
            ...
          }
        }
        """
        eff = {"subjects": {}}

        # -------------------------
        # SEED FROM STATIC POLICY
        # -------------------------
        for subject, cfg in self.static_policy.get("subjects", {}).items():

            eff_subject = eff["subjects"].setdefault(
                subject,
                {"pubs": set(), "subs": set(), "labels": set()}
            )

            for p in cfg.get("pubs", []):
                eff_subject["pubs"].add(p)

            for s in cfg.get("subs", []):
                eff_subject["subs"].add(s)

            for lbl in cfg.get("labels", []):
                eff_subject["labels"].add(lbl)

        # -------------------------
        # APPLY DYNAMIC CAPABILITIES
        # -------------------------
        for ae_id, cap in self.ae_caps.items():

            # Publication requests
            for subject in cap.publishes:
                if subject not in eff["subjects"]:
                    # Not recognized → ignore silently
                    continue

                # Allowed only if static policy already contains ae_id as publisher
                static_publishers = self.static_policy["subjects"].get(subject, {}).get("pubs", [])
                if ae_id in static_publishers:
                    eff["subjects"][subject]["pubs"].add(ae_id)

            # Subscription requests
            for subject in cap.subscribes:
                if subject not in eff["subjects"]:
                    continue

                static_subscribers = self.static_policy["subjects"].get(subject, {}).get("subs", [])
                if ae_id in static_subscribers:
                    eff["subjects"][subject]["subs"].add(ae_id)

        return eff

    # ----------------------------------------------------------------------
    # Permission Checks
    # ----------------------------------------------------------------------
    def can_publish(self, ae_id: str, subject: str) -> bool:
        subject_cfg = self.effective["subjects"].get(subject)
        if not subject_cfg:
            return False
        return ae_id in subject_cfg["pubs"]

    def can_subscribe(self, ae_id: str, subject: str) -> bool:
        subject_cfg = self.effective["subjects"].get(subject)
        if not subject_cfg:
            return False
        return ae_id in subject_cfg["subs"]

    def get_subject_labels(self, subject: str) -> Set[str]:
        subject_cfg = self.effective["subjects"].get(subject)
        if not subject_cfg:
            return set()
        return set(subject_cfg["labels"])

    # ----------------------------------------------------------------------
    # TEST COMPATIBILITY SHIM (support Phase 3F)
    # TODO remove in Phase 4A
    # We are no longer using static in mem local .allow()
    #
    # The abi service run a series of emit tests in test_emit_verified.py
    # We are leaving this shim for a few iteration until phase 4A
    # This sill allow us to continue to test the following
    #       - JWT Auth
    #       - Producer mismatch
    #       - trust validation from keyring
    #       - signature verification (ed25519)
    #       - building envelopes and hashing
    #       - audit logging transport publish() call integrity
    #
    # For now we will inject static policy to ensure all
    # parts are working as we build out the framework through phase 4A
    # ----------------------------------------------------------------------
    def allow(self, subject: str, publisher: str = None, subscriber: str = None, labels=None):
        """
        Compatibility helper ONLY for Phase 3F test suite.

        Allows tests to define synthetic policies without YAML or capabilities.
        This does NOT affect the dynamic policy merge logic.
        """

        # Ensure subject exists
        eff = self.effective.setdefault("subjects", {})
        subj = eff.setdefault(subject, {"pubs": set(), "subs": set(), "labels": set()})

        if publisher:
            subj["pubs"].add(publisher)

        if subscriber:
            subj["subs"].add(subscriber)

        if labels:
            subj["labels"].update(labels)

    # ----------------------------------------------------------------------
    # YAML Loader (Static Policy)
    # ----------------------------------------------------------------------
    # @classmethod
    # def from_yaml(cls, path: str, ae_caps: List[AECapability] = None):
    #     with open(path, "r") as f:
    #         static_policy = yaml.safe_load(f) or {}
    #     return cls(static_policy, ae_caps or [])

# import yaml
# """
# ABI SDK — Policy Engine
# Maps {subject -> allowed publishers/subscribers, labels}.
# In-memory for MVP; pluggable later.
# """
#
# class PolicyEngine:
#     def __init__(self):
#         self.rules = {}
#
#     def allow(self, subject: str, publisher: str = None, subscriber: str = None, labels=None):
#         self.rules.setdefault(subject, {"pubs": set(), "subs": set(), "labels": set()})
#         if publisher:
#             self.rules[subject]["pubs"].add(publisher)
#         if subscriber:
#             self.rules[subject]["subs"].add(subscriber)
#         if labels:
#             self.rules[subject]["labels"].update(labels)
#
#     def can_publish(self, subject, ae_id):
#         rule = self.rules.get(subject)
#         # return True if not rule else ae_id in rule["pubs"]
#         return False if not rule else ae_id in rule["pubs"]
#
#     def can_subscribe(self, subject, ae_id):
#         rule = self.rules.get(subject)
#         # return True if not rule else ae_id in rule["subs"]
#         return False if not rule else ae_id in rule["subs"]
#
#     def get_labels(self, subject):
#         rule = self.rules.get(subject)
#         return rule["labels"] if rule else set()
#
#     # Load Policy from YAML
#     @classmethod
#     def from_yaml(cls, path: str):
#         engine = cls()
#         with open(path, "r") as f:
#             data = yaml.safe_load(f)
#         for subject, conf in data.get("subjects", {}).items():
#             pubs = conf.get("pubs", [])
#             subs = conf.get("subs", [])
#             labels = conf.get("labels", [])
#             for p in pubs:
#                 engine.allow(subject, publisher=p, labels=labels)
#             for s in subs:
#                 engine.allow(subject, subscriber=s, labels=labels)
#         return engine
