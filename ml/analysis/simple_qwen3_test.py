#!/usr/bin/env python3
"""Simple test to check Qwen3 adapter loading."""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

print("Loading base model...")
base_model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen3.5-0.8B",
    torch_dtype=torch.float16,
    device_map="auto",
)

print("Loading adapter...")
adapter_path = "/home/azureuser/inclusify/ml/adapters/qwen3/qwen3_r32_d0.05/checkpoint-150"
model = PeftModel.from_pretrained(base_model, adapter_path)

print("\nChecking parameters...")
lora_count = 0
lora_params = 0
for name, param in model.named_parameters():
    if 'lora' in name.lower():
        lora_count += 1
        lora_params += param.numel()

print(f"LoRA modules found: {lora_count}")
print(f"LoRA parameters: {lora_params:,}")

if lora_params == 0:
    print("\n❌ NO LORA PARAMETERS LOADED!")
    print("This means the adapter is NOT being applied to the model.")
else:
    print(f"\n✓ LoRA adapter loaded successfully")

# Quick inference test
print("\nTesting inference...")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-0.8B")

# Test with clearly problematic text
test_input = "Homosexuality is a mental disorder."
inputs = tokenizer(test_input, return_tensors="pt")
if torch.cuda.is_available():
    inputs = {k: v.cuda() for k, v in inputs.items()}

with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=20)

response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(f"Input: {test_input}")
print(f"Output: {response}")
