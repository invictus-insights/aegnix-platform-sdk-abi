# aegnix_abi/policy.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Set, List, Optional

from aegnix_core.capabilities import AECapability


@dataclass
class PolicyContext:
    """
    PolicyContext
    -------------
    Lightweight container for policy evaluation.

    For 3G:
        - roles are *plumbed through* but *not enforced*.
        - This keeps the API forward-compatible with Phase 4A RBAC.

    Fields:
        ae_id:   Agent Expert identifier (producer/subscriber)
        subject: Topic/subject under evaluation
        roles:   Normalized list of role strings
    """
    ae_id: str
    subject: str
    roles: List[str]


class PolicyEngine:
    """
    Phase 3G — Dynamic Policy Engine

    Combines:
      1. Static policy (config/policy.yaml) — HARD FENCE
      2. Dynamic AE capability declarations (SQLite)
      3. Test-only compatibility shim for 3F/3G (`allow()`)

    NOTE on roles (Step 3.3):
        - Roles are accepted and normalized
        - They are *not* enforced yet
        - RBAC logic will be added in Phase 4A
    """

    def __init__(self, static_policy: Dict | None = None, ae_caps: List[AECapability] | None = None):
        self.static_policy: Dict = static_policy or {}
        self.ae_caps: Dict[str, AECapability] = {c.ae_id: c for c in (ae_caps or [])}

        # Effective policy is built from:
        #   - static_policy["subjects"]
        #   - ae_caps (dynamic)
        self.effective: Dict = self._build_effective_policy()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_roles(roles: Optional[str | List[str]]) -> List[str]:
        """
        Normalize roles into a list of strings.

        Accepts:
            - None              → []
            - "producer,analytics" → ["producer", "analytics"]
            - ["producer"]      → ["producer"]

        For 3.3 this is *metadata only*; no enforcement yet.
        """
        if roles is None:
            return []
        if isinstance(roles, str):
            return [r.strip() for r in roles.split(",") if r.strip()]
        return [str(r).strip() for r in roles if str(r).strip()]

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
        eff: Dict[str, Dict] = {"subjects": {}}

        # -------------------------
        # SEED FROM STATIC POLICY
        # -------------------------
        for subject, cfg in self.static_policy.get("subjects", {}).items():
            eff_subject = eff["subjects"].setdefault(
                subject,
                {"pubs": set(), "subs": set(), "labels": set()},
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
                    # Unknown subject → ignore
                    continue

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

    # ------------------------------------------------------------------
    # Permission Checks (role-aware API, no enforcement yet)
    # ------------------------------------------------------------------
    def can_publish(self, ae_id: str, subject: str, roles: Optional[str | List[str]] = None) -> bool:
        """
        Determine if AE may publish to a subject.

        3G behavior:
            • subject must exist in effective policy
            • AE must be listed as publisher in effective["subjects"][subject]["pubs"]
            • roles are accepted/normalized but NOT enforced yet
        """
        ctx = PolicyContext(
            ae_id=ae_id,
            subject=subject,
            roles=self._normalize_roles(roles),
        )

        subject_cfg = self.effective["subjects"].get(ctx.subject)
        if not subject_cfg:
            return False

        return ctx.ae_id in subject_cfg["pubs"]

    def can_subscribe(self, ae_id: str, subject: str, roles: Optional[str | List[str]] = None) -> bool:
        """
        Determine if AE may subscribe to a subject.

        3G behavior:
            • subject must exist in effective policy
            • AE must be listed as subscriber in effective["subjects"][subject]["subs"]
            • roles are accepted/normalized but NOT enforced yet
        """
        ctx = PolicyContext(
            ae_id=ae_id,
            subject=subject,
            roles=self._normalize_roles(roles),
        )

        subject_cfg = self.effective["subjects"].get(ctx.subject)
        if not subject_cfg:
            return False

        return ctx.ae_id in subject_cfg["subs"]

    # ------------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------------
    def get_subject_labels(self, subject: str) -> Set[str]:
        """
        Return static labels for a subject.

        NOTE:
            Dynamic capabilities CANNOT change labels.
        """
        subject_cfg = self.effective["subjects"].get(subject)
        if not subject_cfg:
            return set()
        return set(subject_cfg["labels"])

    # ------------------------------------------------------------------
    # TEST COMPATIBILITY SHIM (support Phase 3F)
    # TODO remove in Phase 4A
    #
    # The ABI service emit tests (test_emit_verified.py) still rely on
    # a lightweight way to inject subjects/pubs/subs without YAML or
    # capabilities. This shim mutates the effective map *after* init.
    # ------------------------------------------------------------------
    def allow(self, subject: str, publisher: str = None, subscriber: str = None, labels=None):
        """
        Test-only helper for 3F → 3G transition.

        Allows tests to simulate policy rules without a YAML file
        or capability declarations.

        THIS WILL BE REMOVED IN PHASE 4A.
        """
        subj = self.effective["subjects"].setdefault(
            subject,
            {"pubs": set(), "subs": set(), "labels": set()},
        )

        if publisher:
            subj["pubs"].add(publisher)

        if subscriber:
            subj["subs"].add(subscriber)

        if labels:
            subj["labels"].update(labels or [])


# # aegnix_abi/policy.py
#
# from __future__ import annotations
# from typing import Dict, Set, List
# import yaml
#
# from aegnix_core.capabilities import AECapability
#
#
# class PolicyEngine:
#     def __init__(self, static_policy: dict | None = None, ae_caps=None):
#         """
#         static_policy:
#             Parsed YAML dict containing:
#               - subjects: {...}
#               - roles: {...} (ignored in 3G)
#         """
#         self.static = static_policy or {}
#         self.subjects = self.static.get("subjects", {})
#         self.role_config = self.static.get("roles", {}) or {}
#
#         self.ae_caps = {c.ae_id: c for c in (ae_caps or [])}
#
#         # compatibility mode (used only by test suite via .allow())
#         self._compat = {"subjects": {}}
#
#         # Build effective policy IMMEDIATELY
#         self.effective = self._build_effective_policy()
#
#
#     # ------------------------------------------------------------------
#     # BUILD EFFECTIVE POLICY
#     # ------------------------------------------------------------------
#     def _build_effective_policy(self):
#         """
#         Returns merged static + dynamic policy.
#
#         Output schema:
#         {
#             "subjects": {
#                 "fusion.topic": {
#                     "pubs": set([...]),
#                     "subs": set([...]),
#                     "labels": set([...])
#                 },
#                 ...
#             }
#         }
#         """
#         eff = {"subjects": {}}
#
#         # 1) Seed from static
#         for subject, cfg in self.subjects.items():
#             eff["subjects"][subject] = {
#                 "pubs": set(cfg.get("pubs", [])),
#                 "subs": set(cfg.get("subs", [])),
#                 "labels": set(cfg.get("labels", [])),  # immutable
#             }
#
#         # 2) Apply dynamic capabilities (3G rules)
#         for ae_id, cap in self.ae_caps.items():
#
#             # Dynamic publish enrichment
#             for subject in cap.publishes:
#                 if subject not in eff["subjects"]:
#                     # unknown subject → ignore silently
#                     continue
#
#                 static_publishers = self.subjects.get(subject, {}).get("pubs", [])
#                 if ae_id in static_publishers:
#                     eff["subjects"][subject]["pubs"].add(ae_id)
#
#             # Dynamic subscribe enrichment
#             for subject in cap.subscribes:
#                 if subject not in eff["subjects"]:
#                     continue
#
#                 static_subscribers = self.subjects.get(subject, {}).get("subs", [])
#                 if ae_id in static_subscribers:
#                     eff["subjects"][subject]["subs"].add(ae_id)
#
#         # 3) Compatibility entries from .allow()
#         for subject, cfg in self._compat["subjects"].items():
#             eff["subjects"].setdefault(subject, {
#                 "pubs": set(),
#                 "subs": set(),
#                 "labels": set(),
#             })
#             eff["subjects"][subject]["pubs"].update(cfg.get("pubs", []))
#             eff["subjects"][subject]["subs"].update(cfg.get("subs", []))
#             eff["subjects"][subject]["labels"].update(cfg.get("labels", []))
#
#         return eff
#
#
#     # ------------------------------------------------------------------
#     # ACCESSORS
#     # ------------------------------------------------------------------
#     def can_publish(self, ae_id: str, subject: str, roles=None):
#         cfg = self.effective["subjects"].get(subject)
#         if not cfg:
#             return False
#         return ae_id in cfg["pubs"]
#
#     def can_subscribe(self, ae_id: str, subject: str, roles=None):
#         cfg = self.effective["subjects"].get(subject)
#         if not cfg:
#             return False
#         return ae_id in cfg["subs"]
#
#     def get_subject_labels(self, subject: str):
#         cfg = self.effective["subjects"].get(subject)
#         if not cfg:
#             return set()
#         return set(cfg["labels"])
#
#     # ----------------------------------------------------------------------
#     # TEST COMPATIBILITY SHIM (support Phase 3F)
#     # TODO remove in Phase 4A
#     # We are no longer using static in mem local .allow()
#     #
#     # The abi service run a series of emit tests in test_emit_verified.py
#     # We are leaving this shim for a few iteration until phase 4A
#     # This sill allow us to continue to test the following
#     #       - JWT Auth
#     #       - Producer mismatch
#     #       - trust validation from keyring
#     #       - signature verification (ed25519)
#     #       - building envelopes and hashing
#     #       - audit logging transport publish() call integrity
#     #
#     # For now we will inject static policy to ensure all
#     # parts are working as we build out the framework through phase 4A
#     # ----------------------------------------------------------------------
#     def allow(self, subject: str, publisher: str = None, subscriber: str = None, labels=None):
#         """
#         Test-only helper for 3F → 3G transition.
#
#         Allows tests to simulate policy rules without a YAML file
#         or capability declarations.
#
#         THIS WILL BE REMOVED IN PHASE 4A.
#         """
#         subj = self.effective["subjects"].setdefault(
#             subject,
#             {"pubs": set(), "subs": set(), "labels": set()}
#         )
#
#         if publisher:
#             subj["pubs"].add(publisher)
#
#         if subscriber:
#             subj["subs"].add(subscriber)
#
#         if labels:
#             subj["labels"].update(labels)
#
