from transformers import pipeline
import torch
import sys

print("Checking BERT model status...")
try:
    # Try to load the model from local cache only
    classifier = pipeline(
        "zero-shot-classification",
        model="valhalla/distilbart-mnli-12-1",
        local_files_only=True
    )
    print("SUCCESS: Model is fully downloaded and cached!")
    sys.exit(0)
except Exception as e:
    print(f"NOT READY: Model is not found in local cache or is incomplete.")
    print(f"Reason: {str(e)}")
    sys.exit(1)
