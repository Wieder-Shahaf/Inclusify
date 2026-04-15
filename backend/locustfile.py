import os
from locust import HttpUser, task, between

class VLLMAnalysisTester(HttpUser):
    # Wait between 1 and 3 seconds before executing the next task
    wait_time = between(1, 3)

    @task
    def analyze_text(self):
        # A sample text string containing flagged rule-based and LLM-targeted terms in Hebrew and English
        payload = {
            "text": "This is a sample document evaluating the homosexual lifestyle choice. We need to ensure that normal people are respected and that someone born a man is treated fairly. בנוסף, חשוב לזכור שהעדפה מינית היא חלק מהחיים, ואין להפלות הומוסקסואל.",
            "language": "auto",
            "private_mode": False
        }
        
        # Open a POST request to the analyze endpoint. 
        # Using a timeout of 120 seconds in case the vLLM endpoint queues requests under load
        with self.client.post("/api/v1/analysis/analyze", json=payload, catch_response=True, timeout=120) as response:
            if response.status_code == 200:
                response.success()
            else:
                # Capture and log specific HTTP errors in the Locust UI
                response.failure(f"Failed {response.status_code}: {response.text[:200]}")
