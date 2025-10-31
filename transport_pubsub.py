"""
ABI SDK — GCP Pub/Sub Adapter (MVP)
Simple abstraction for audit publishing.
"""

from google.cloud import pubsub_v1

class PubSubAdapter:
    def __init__(self, project_id):
        self.project_id = project_id
        self.publisher = pubsub_v1.PublisherClient()

    def publish(self, topic, data: bytes):
        topic_path = f"projects/{self.project_id}/topics/{topic}"
        future = self.publisher.publish(topic_path, data=data)
        return future.result()
