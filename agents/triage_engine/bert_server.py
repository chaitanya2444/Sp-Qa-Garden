from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
from transformers import pipeline
import torch
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---- Request/Response Models ----

class BertRequest(BaseModel):
    text: str
    labels: Optional[List[str]] = None


class BertResponse(BaseModel):
    label: str
    confidence: float
    scores: Dict[str, float]


# ---- AI Model Initialization ----

print("Loading BERT Classification Model...")
# Using a DistilBART model for a good balance of speed and accuracy
device = 0 if torch.cuda.is_available() else -1
classifier = pipeline(
    "zero-shot-classification",
    model="valhalla/distilbart-mnli-12-1",
    device=device
)
print(f"Model loaded successfully on {'GPU' if device == 0 else 'CPU'}")

# ---- FastAPI app ----

app = FastAPI(title="BERT Classification Server")


@app.get("/")
async def root():
    return {
        "status": "ok", 
        "service": "bert_server", 
        "model": "distilbart-mnli-12-1",
        "device": "cuda" if device == 0 else "cpu"
    }


@app.post("/predict", response_model=BertResponse)
async def predict(request: BertRequest):
    """
    Real BERT-based Zero-Shot Classifier.
    Classifies error text into the provided candidate labels.
    """
    if not request.labels:
        raise HTTPException(status_code=400, detail="No candidate labels provided")

    try:
        # Perform classification
        result = classifier(
            request.text,
            candidate_labels=request.labels,
            multi_label=False
        )

        # Extract results
        best_label = result["labels"][0]
        best_score = result["scores"][0]
        
        # Create full scores dictionary
        scores = {label: score for label, score in zip(result["labels"], result["scores"])}

        return BertResponse(
            label=best_label,
            confidence=best_score,
            scores=scores,
        )

    except Exception as e:
        print(f"Prediction error: {str(e)}")
        # Fallback to dummy behavior if model fails
        return BertResponse(
            label=request.labels[0],
            confidence=0.0,
            scores={lbl: 0.0 for lbl in request.labels}
        )


if __name__ == "__main__":
    port = int(os.getenv("BERT_SERVER_PORT", 8001))
    host = os.getenv("BERT_SERVER_HOST", "0.0.0.0")
    
    uvicorn.run(
        "bert_server:app",
        host=host,
        port=port,
        reload=False
    )

