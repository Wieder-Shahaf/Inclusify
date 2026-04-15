import sys
from locust import HttpUser, task, between

# We use a static sample text to simulate typical anaylsis payloads
SAMPLE_TEXT = (
    "This is a sample text for analyzing the performance of the vLLM model. "
    "We use it to simulate an average request length containing enough tokens "
    "to trigger meaningful GPU usage. The system should process this using the LLM "
    "and return any potential inclusive language issues."
)

class VllmAnalysisTester(HttpUser):
    # Wait between 1 and 3 seconds before executing the next task
    wait_time = between(1, 3)

    @task
    def analyze_text(self):
        # We use private_mode=True so we don't bombard the database with load testing garbage
        payload = {
            "text": SAMPLE_TEXT,
            "language": "en",
            "private_mode": True 
        }
        
        # Open a POST request to the analysis endpoint with JSON
        with self.client.post("/api/v1/analysis/analyze", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                # Capture and log specific HTTP errors in the Locust UI
                response.failure(f"Failed {response.status_code}: {response.text[:200]}")
