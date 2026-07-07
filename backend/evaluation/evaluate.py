import json
import os
import sys
import time
import requests
import pandas as pd
from pathlib import Path

try:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy,
    )
except ImportError:
    print("Please install required packages: pip install ragas datasets pandas")
    sys.exit(1)

# Ensure environment has OpenAI API Key for Ragas
if "OPENAI_API_KEY" not in os.environ:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")

API_URL = "http://localhost:8000/chat"

def run_evaluation(limit=10):
    dataset_path = Path(__file__).parent / "dataset.json"
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}. Please run prepare_dataset.py first.")
        return
        
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} examples from dataset.")
    if limit and limit < len(data):
        print(f"Limiting to first {limit} examples for evaluation.")
        data = data[:limit]
        
    questions = []
    answers = []
    contexts = []
    ground_truths = []
    
    print("Sending queries to backend RAG API...")
    for idx, item in enumerate(data):
        question = item["question"]
        print(f"[{idx+1}/{len(data)}] Query: {question[:50]}...")
        
        try:
            response = requests.post(API_URL, json={"query": question}, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            answer_text = result.get("response", "")
            # Extract text from context_used objects
            context_objs = result.get("context_used", [])
            retrieved_contexts = [ctx.get("content", "") for ctx in context_objs]
            
            questions.append(question)
            answers.append(answer_text)
            contexts.append(retrieved_contexts)
            # Ragas expects ground_truths as list of strings (for multiple acceptable answers) or a single string depending on version.
            # Ragas v0.1.0+ prefers "ground_truth" as string, but previously "ground_truths" as list of strings.
            ground_truths.append(item["ground_truth"])
            
        except Exception as e:
            print(f"  -> Error querying API: {e}")
            # Append empty to maintain list lengths
            questions.append(question)
            answers.append("Error")
            contexts.append([])
            ground_truths.append(item["ground_truth"])
            
    # Build Ragas Dataset
    eval_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }
    
    dataset = Dataset.from_dict(eval_dict)
    
    print("\nStarting Ragas Evaluation (this may take a while)...")
    
    metrics = [
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy
    ]
    
    try:
        results = evaluate(dataset, metrics=metrics)
        print("\n=== Evaluation Results ===")
        print(results)
        
        # Export to CSV
        df = results.to_pandas()
        out_csv = Path(__file__).parent / "results.csv"
        df.to_csv(out_csv, index=False, encoding="utf-8-sig")
        print(f"\nDetailed results saved to {out_csv}")
        
    except Exception as e:
        print(f"Evaluation failed: {e}")

if __name__ == "__main__":
    # You can change limit to None to run on the full dataset
    run_evaluation(limit=10)
