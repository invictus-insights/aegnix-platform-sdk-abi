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

