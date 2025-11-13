"""
ABI SDK — Policy Engine
Maps {subject -> allowed publishers/subscribers, labels}.
In-memory for MVP; pluggable later.
"""

class PolicyEngine:
    def __init__(self):
        self.rules = {}

    def allow(self, subject: str, publisher: str = None, subscriber: str = None, labels=None):
        self.rules.setdefault(subject, {"pubs": set(), "subs": set(), "labels": set()})
        if publisher:
            self.rules[subject]["pubs"].add(publisher)
        if subscriber:
            self.rules[subject]["subs"].add(subscriber)
        if labels:
            self.rules[subject]["labels"].update(labels)

    def can_publish(self, subject, ae_id):
        rule = self.rules.get(subject)
        # return True if not rule else ae_id in rule["pubs"]
        return False if not rule else ae_id in rule["pubs"]

    def can_subscribe(self, subject, ae_id):
        rule = self.rules.get(subject)
        # return True if not rule else ae_id in rule["subs"]
        return False if not rule else ae_id in rule["subs"]

    def get_labels(self, subject):
        rule = self.rules.get(subject)
        return rule["labels"] if rule else set()
