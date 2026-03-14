#!/usr/bin/env python3
"""
Test vLLM with Qwen2.5-3B + LoRA adapter.
"""

from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

print("="*70)
print("Testing vLLM with Qwen2.5-3B + LoRA")
print("="*70)

# Initialize vLLM
print("\nInitializing vLLM...")
import os
# Set environment variable to use pre-compiled kernels (no JIT needed)
os.environ['VLLM_ATTENTION_BACKEND'] = 'XFORMERS'

llm = LLM(
    model="Qwen/Qwen2.5-3B-Instruct",
    enable_lora=True,
    max_lora_rank=16,  # Our adapter uses rank 8
    max_num_seqs=8,  # Start with moderate batching
    gpu_memory_utilization=0.9,
    trust_remote_code=True,
    dtype="float16",
    enforce_eager=False,  # Use CUDA graphs for better performance
)

print("✓ vLLM initialized successfully!")

# Create LoRA request
lora_request = LoRARequest(
    lora_name="inclusify",
    lora_int_id=1,
    lora_path="/home/azureuser/inclusify/ml/adapters/qwen_r8_d0.2"
)

print(f"✓ LoRA adapter loaded: {lora_request.lora_path}")

# Sampling parameters
sampling_params = SamplingParams(
    temperature=0.1,
    max_tokens=10,
    stop=["<|im_end|>"],
)

# Test prompts
system_prompt = """You are an LGBTQ+ inclusive language analyzer. Analyze the following academic text and determine if it contains problematic language.

Respond with ONLY ONE WORD:
- "problematic" if the text contains LGBTQphobic, outdated, biased, or pathologizing language
- "appropriate" if the text uses inclusive and respectful language"""

test_cases = [
    ("Homosexuality is a mental disorder that needs treatment.", "problematic"),
    ("Gender dysphoria is recognized by major medical associations.", "appropriate"),
    ("The LGBT lifestyle is harmful to society.", "problematic"),
    ("Same-sex couples deserve equal rights and recognition.", "appropriate"),
    ("Sexual orientation conversion therapy is effective.", "problematic"),
]

print("\n" + "="*70)
print("Testing Inference")
print("="*70)

prompts = []
for text, expected in test_cases:
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n"
    prompts.append(prompt)

# Generate
print("\nRunning batch inference...")
outputs = llm.generate(
    prompts,
    sampling_params,
    lora_request=lora_request,
)

# Check results
print("\nResults:")
print("-" * 70)
correct = 0
for i, (output, (text, expected)) in enumerate(zip(outputs, test_cases)):
    response = output.outputs[0].text.strip().lower()
    predicted = "problematic" if "problematic" in response else "appropriate"
    is_correct = "✓" if predicted == expected else "✗"

    if predicted == expected:
        correct += 1

    print(f"\n{i+1}. Input: {text[:60]}...")
    print(f"   Expected: {expected}")
    print(f"   Predicted: {predicted} {is_correct}")
    print(f"   Raw output: {output.outputs[0].text}")

accuracy = correct / len(test_cases) * 100
print("\n" + "="*70)
print(f"Accuracy: {correct}/{len(test_cases)} ({accuracy:.0f}%)")
print("="*70)

if accuracy >= 80:
    print("\n✅ vLLM + LoRA deployment successful!")
else:
    print("\n⚠️  Accuracy below 80% - may need debugging")

print("\n✓ Test complete")
