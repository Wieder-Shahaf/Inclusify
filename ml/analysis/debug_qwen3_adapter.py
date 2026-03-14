#!/usr/bin/env python3
"""
Debug script to investigate Qwen3.5 adapter loading and inference issues.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_adapter_loading():
    """Test if adapter loads correctly and check weights."""

    print("="*70)
    print("DEBUGGING QWEN3.5 ADAPTER")
    print("="*70)

    adapter_path = "/home/azureuser/inclusify/ml/adapters/qwen3/qwen3_r32_d0.05/checkpoint-150"

    print(f"\n1. Loading base model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen3.5-0.8B",
        torch_dtype=torch.float16,
        device_map="auto",
    )
    print(f"   Base model loaded: {base_model.__class__.__name__}")

    print(f"\n2. Loading adapter from: {adapter_path}")
    try:
        model = PeftModel.from_pretrained(base_model, adapter_path)
        print(f"   Adapter loaded: {model.__class__.__name__}")
    except Exception as e:
        print(f"   ERROR loading adapter: {e}")
        return

    print(f"\n3. Checking adapter modules...")
    adapter_params = 0
    base_params = 0

    for name, param in model.named_parameters():
        if 'lora' in name.lower():
            adapter_params += param.numel()
            if adapter_params < 10:  # Print first few
                print(f"   LoRA param: {name}, shape: {param.shape}")
        else:
            base_params += 1

    print(f"\n   Total LoRA parameters: {adapter_params:,}")
    print(f"   Base parameters (frozen): {base_params:,}")

    if adapter_params == 0:
        print("\n   ⚠️  WARNING: No LoRA parameters found! Adapter not loaded correctly.")
        return False

    print(f"\n4. Testing inference...")
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-0.8B")

    test_text = "Gender dysphoria is a mental illness that needs to be cured."
    system_prompt = """You are an LGBTQ+ inclusive language analyzer. Analyze the following academic text and determine if it contains problematic language.

Respond with ONLY ONE WORD:
- "problematic" if the text contains LGBTQphobic, outdated, biased, or pathologizing language
- "appropriate" if the text uses inclusive and respectful language"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": test_text}
    ]

    formatted = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(formatted, return_tensors="pt", padding=True)
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}

    print(f"   Input: {test_text}")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=50,
            temperature=0.1,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    print(f"   Response: '{response.strip()}'")

    # Test with appropriate text
    test_text2 = "Gender dysphoria is recognized by major medical associations as a real clinical condition."
    messages[1]["content"] = test_text2
    formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(formatted, return_tensors="pt", padding=True)
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}

    print(f"\n   Input: {test_text2}")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=50,
            temperature=0.1,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    print(f"   Response: '{response.strip()}'")

    print("\n5. Testing with Unsloth loading (if available)...")
    try:
        from unsloth import FastLanguageModel

        print("   Unsloth available! Testing with Unsloth loader...")
        model_unsloth, tokenizer_unsloth = FastLanguageModel.from_pretrained(
            model_name="Qwen/Qwen3.5-0.8B",
            max_seq_length=2048,
            dtype=torch.float16,
            load_in_4bit=False,
        )

        # Load adapter
        from peft import PeftModel
        model_unsloth = PeftModel.from_pretrained(model_unsloth, adapter_path)

        print("   Testing inference with Unsloth-loaded model...")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": test_text}
        ]
        formatted = tokenizer_unsloth.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer_unsloth(formatted, return_tensors="pt", padding=True)
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model_unsloth.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.1,
                do_sample=False,
                pad_token_id=tokenizer_unsloth.pad_token_id,
                eos_token_id=tokenizer_unsloth.eos_token_id,
            )

        response = tokenizer_unsloth.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        print(f"   Unsloth Response: '{response.strip()}'")

    except ImportError:
        print("   Unsloth not available, skipping...")

    print("\n" + "="*70)
    print("Debug complete!")
    print("="*70)

    return True


if __name__ == "__main__":
    test_adapter_loading()
