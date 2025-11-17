# aegnix_abi/policy.py

from __future__ import annotations
from typing import Dict, Set, List
import yaml

from aegnix_core.capabilities import AECapability


class PolicyEngine:
    def __init__(self, static_policy: dict | None = None, ae_caps=None):
        """
        static_policy:
            Parsed YAML dict containing:
              - subjects: {...}
              - roles: {...} (ignored in 3G)
        """
        self.static = static_policy or {}
        self.subjects = self.static.get("subjects", {})
        self.role_config = self.static.get("roles", {}) or {}

        self.ae_caps = {c.ae_id: c for c in (ae_caps or [])}

        # compatibility mode (used only by test suite via .allow())
        self._compat = {"subjects": {}}

        # Build effective policy IMMEDIATELY
        self.effective = self._build_effective_policy()


    # ------------------------------------------------------------------
    # BUILD EFFECTIVE POLICY
    # ------------------------------------------------------------------
    def _build_effective_policy(self):
        """
        Returns merged static + dynamic policy.

        Output schema:
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

        # 1) Seed from static
        for subject, cfg in self.subjects.items():
            eff["subjects"][subject] = {
                "pubs": set(cfg.get("pubs", [])),
                "subs": set(cfg.get("subs", [])),
                "labels": set(cfg.get("labels", [])),  # immutable
            }

        # 2) Apply dynamic capabilities (3G rules)
        for ae_id, cap in self.ae_caps.items():

            # Dynamic publish enrichment
            for subject in cap.publishes:
                if subject not in eff["subjects"]:
                    # unknown subject → ignore silently
                    continue

                static_publishers = self.subjects.get(subject, {}).get("pubs", [])
                if ae_id in static_publishers:
                    eff["subjects"][subject]["pubs"].add(ae_id)

            # Dynamic subscribe enrichment
            for subject in cap.subscribes:
                if subject not in eff["subjects"]:
                    continue

                static_subscribers = self.subjects.get(subject, {}).get("subs", [])
                if ae_id in static_subscribers:
                    eff["subjects"][subject]["subs"].add(ae_id)

        # 3) Compatibility entries from .allow()
        for subject, cfg in self._compat["subjects"].items():
            eff["subjects"].setdefault(subject, {
                "pubs": set(),
                "subs": set(),
                "labels": set(),
            })
            eff["subjects"][subject]["pubs"].update(cfg.get("pubs", []))
            eff["subjects"][subject]["subs"].update(cfg.get("subs", []))
            eff["subjects"][subject]["labels"].update(cfg.get("labels", []))

        return eff


    # ------------------------------------------------------------------
    # ACCESSORS
    # ------------------------------------------------------------------
    def can_publish(self, ae_id: str, subject: str, roles=None):
        cfg = self.effective["subjects"].get(subject)
        if not cfg:
            return False
        return ae_id in cfg["pubs"]

    def can_subscribe(self, ae_id: str, subject: str, roles=None):
        cfg = self.effective["subjects"].get(subject)
        if not cfg:
            return False
        return ae_id in cfg["subs"]

    def get_subject_labels(self, subject: str):
        cfg = self.effective["subjects"].get(subject)
        if not cfg:
            return set()
        return set(cfg["labels"])

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
        Test-only helper for 3F → 3G transition.

        Allows tests to simulate policy rules without a YAML file
        or capability declarations.

        THIS WILL BE REMOVED IN PHASE 4A.
        """
        subj = self.effective["subjects"].setdefault(
            subject,
            {"pubs": set(), "subs": set(), "labels": set()}
        )

        if publisher:
            subj["pubs"].add(publisher)

        if subscriber:
            subj["subs"].add(subscriber)

        if labels:
            subj["labels"].update(labels)

