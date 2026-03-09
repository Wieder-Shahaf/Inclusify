#!/usr/bin/env python3
"""
Inclusify Inference Service
============================

A lightweight FastAPI service that provides OpenAI-compatible API endpoints
using transformers + LoRA adapters directly (no vLLM dependency).

Designed for T4 GPU compatibility using bitsandbytes 4-bit quantization.

Usage:
    python inference_service.py --port 8001

API Endpoints:
    POST /v1/chat/completions - OpenAI-compatible chat completions
    GET /health - Health check
"""

import argparse
import json
import logging
import re
import time
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

warnings.filterwarnings('ignore')

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global model state
_model = None
_tokenizer = None


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    max_tokens: int = 256
    temperature: float = 0.1


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[dict]
    usage: dict


def load_model(adapter_path: str = "/home/azureuser/inclusify/ml/LoRA_Adapters"):
    """Load the model with LoRA adapter at startup."""
    global _model, _tokenizer

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    base_model_id = "lightblue/suzume-llama-3-8B-multilingual"

    logger.info("Loading tokenizer...")
    _tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    logger.info(f"Loading base model ({base_model_id}) with 4-bit quantization...")

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )

    # Use SDPA (PyTorch native scaled dot product attention) - T4 compatible
    _model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        quantization_config=quantization_config,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="sdpa",
    )

    if Path(adapter_path).exists():
        logger.info(f"Loading LoRA adapter from {adapter_path}...")
        _model = PeftModel.from_pretrained(_model, adapter_path)
        logger.info("LoRA adapter loaded successfully!")
    else:
        logger.warning(f"Adapter not found at {adapter_path}. Using base model.")

    _model.eval()

    # Try torch.compile for faster inference
    try:
        _model = torch.compile(_model, mode="reduce-overhead")
        logger.info("Model compiled with torch.compile()")
    except Exception as e:
        logger.warning(f"torch.compile() not available: {e}")

    device = next(_model.parameters()).device
    logger.info(f"Model ready on device: {device}")

    return _model, _tokenizer


def generate_response(messages: list[Message], max_tokens: int = 256) -> tuple[str, float]:
    """Generate response from the model. Returns (content, inference_time_ms)."""
    import torch

    global _model, _tokenizer

    # Convert messages to chat format
    chat_messages = [{"role": m.role, "content": m.content} for m in messages]

    input_ids = _tokenizer.apply_chat_template(
        chat_messages,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to(_model.device)

    attention_mask = torch.ones_like(input_ids)

    terminators = [
        _tokenizer.eos_token_id,
        _tokenizer.convert_tokens_to_ids("<|eot_id|>")
    ]

    start_time = time.perf_counter()

    with torch.inference_mode():
        outputs = _model.generate(
            input_ids,
            attention_mask=attention_mask,
            max_new_tokens=min(max_tokens, 512),
            eos_token_id=terminators,
            do_sample=False,
            pad_token_id=_tokenizer.eos_token_id,
            use_cache=True,
        )

    inference_time_ms = (time.perf_counter() - start_time) * 1000

    response = outputs[0][input_ids.shape[-1]:]
    content = _tokenizer.decode(response, skip_special_tokens=True)

    return content, inference_time_ms


# CLI argument parsing (before app creation for lifespan)
parser = argparse.ArgumentParser(description='Inclusify Inference Service')
parser.add_argument('--port', type=int, default=8001, help='Port to run on')
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to')
parser.add_argument('--adapter-path', type=str, default='/home/azureuser/inclusify/ml/LoRA_Adapters',
                    help='Path to LoRA adapter directory')
args, _ = parser.parse_known_args()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup."""
    logger.info("Starting Inclusify Inference Service...")
    load_model(adapter_path=args.adapter_path)
    logger.info("Model loaded, service ready!")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Inclusify Inference Service",
    description="OpenAI-compatible API for LGBTQ+ inclusive language analysis",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "model_loaded": _model is not None}


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint."""
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        content, inference_time_ms = generate_response(request.messages, request.max_tokens)

        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": 0,  # Not tracking for now
                "completion_tokens": 0,
                "total_tokens": 0,
                "inference_time_ms": inference_time_ms
            }
        )
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
