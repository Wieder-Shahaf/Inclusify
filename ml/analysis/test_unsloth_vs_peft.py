#!/usr/bin/env python3
"""
Test loading Qwen3 adapter with both standard PEFT and Unsloth to compare.
"""

import torch
from transformers import AutoTokenizer

print("="*70)
print("TESTING: Standard PEFT vs Unsloth Loading")
print("="*70)

adapter_path = "/home/azureuser/inclusify/ml/adapters/qwen3/qwen3_r32_d0.05/checkpoint-150"

# Test 1: Standard PEFT loading (what evaluation script uses)
print("\n[TEST 1] Loading with standard PEFT...")
try:
    from transformers import AutoModelForCausalLM
    from peft import PeftModel

    base_model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen3.5-0.8B",
        torch_dtype=torch.float16,
        device_map="auto",
    )

    model_peft = PeftModel.from_pretrained(base_model, adapter_path)

    # Count LoRA params
    lora_params = sum(p.numel() for n, p in model_peft.named_parameters() if 'lora' in n.lower())
    total_params = sum(p.numel() for p in model_peft.parameters())

    print(f"✓ Loaded with PEFT")
    print(f"  LoRA parameters: {lora_params:,}")
    print(f"  Total parameters: {total_params:,}")
    print(f"  LoRA ratio: {lora_params/total_params*100:.2f}%")

    del base_model, model_peft
    torch.cuda.empty_cache()

except Exception as e:
    print(f"✗ PEFT loading failed: {e}")

# Test 2: Unsloth loading
print("\n[TEST 2] Loading with Unsloth...")
try:
    from unsloth import FastLanguageModel

    # Load base model with Unsloth
    model_unsloth, tokenizer = FastLanguageModel.from_pretrained(
        model_name="Qwen/Qwen3.5-0.8B",
        max_seq_length=2048,
        dtype=torch.float16,
        load_in_4bit=False,
    )

    # Load adapter using PEFT on top of Unsloth model
    from peft import PeftModel
    model_unsloth = PeftModel.from_pretrained(model_unsloth, adapter_path)

    # Count LoRA params
    lora_params = sum(p.numel() for n, p in model_unsloth.named_parameters() if 'lora' in n.lower())
    total_params = sum(p.numel() for p in model_unsloth.parameters())

    print(f"✓ Loaded with Unsloth")
    print(f"  LoRA parameters: {lora_params:,}")
    print(f"  Total parameters: {total_params:,}")
    print(f"  LoRA ratio: {lora_params/total_params*100:.2f}%")

    # Test inference
    print("\n[TEST 3] Testing inference with Unsloth model...")
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-0.8B")

    system_prompt = """You are an LGBTQ+ inclusive language analyzer. Analyze the following academic text and determine if it contains problematic language.

Respond with ONLY ONE WORD:
- "problematic" if the text contains LGBTQphobic, outdated, biased, or pathologizing language
- "appropriate" if the text uses inclusive and respectful language"""

    # Test problematic text
    test_text = "Homosexuality is a mental disorder that needs treatment."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": test_text}
    ]

    formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(formatted, return_tensors="pt", padding=True)
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model_unsloth.generate(
            **inputs,
            max_new_tokens=10,
            temperature=0.1,
            do_sample=False,
        )

    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    print(f"  Input: '{test_text}'")
    print(f"  Output: '{response.strip()}'")
    print(f"  Expected: 'problematic'")

except Exception as e:
    print(f"✗ Unsloth loading failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
