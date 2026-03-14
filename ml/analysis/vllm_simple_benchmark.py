#!/usr/bin/env python3
"""
Simple vLLM benchmark with merged model (no LoRA) to test max throughput.
Then we'll compare with LoRA version if compatibility allows.
"""

import time
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

def merge_lora_adapter():
    """Merge LoRA adapter into base model for faster inference."""
    print("="*70)
    print("STEP 1: Merging LoRA Adapter into Base Model")
    print("="*70)

    print("\nLoading base model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-3B-Instruct",
        torch_dtype=torch.float16,
        device_map="auto",
    )

    print("Loading LoRA adapter...")
    peft_model = PeftModel.from_pretrained(
        base_model,
        "/home/azureuser/inclusify/ml/adapters/qwen_r8_d0.2"
    )

    print("Merging LoRA weights into base model...")
    merged_model = peft_model.merge_and_unload()

    output_path = "/home/azureuser/inclusify/ml/models/qwen25-inclusify-merged"
    print(f"Saving merged model to: {output_path}")
    merged_model.save_pretrained(output_path)

    # Save tokenizer too
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct")
    tokenizer.save_pretrained(output_path)

    print(f"✓ Merged model saved to: {output_path}")

    del base_model, peft_model, merged_model
    torch.cuda.empty_cache()

    return output_path


def benchmark_merged_model(model_path, num_requests=100):
    """Benchmark the merged model with optimizations."""
    print("\n" + "="*70)
    print("STEP 2: Benchmarking Merged Model")
    print("="*70)

    from transformers import AutoModelForCausalLM, AutoTokenizer

    print("\nLoading merged model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model.eval()

    # Enable torch compile for 2x speedup
    print("Compiling model with torch.compile...")
    try:
        model.generate = torch.compile(model.generate, mode="reduce-overhead")
        print("✓ Model compiled")
    except Exception as e:
        print(f"⚠️  Compilation failed (will use uncompiled): {e}")

    print(f"\n✓ Merged model loaded")

    # Test samples
    test_samples = [
        "Gender dysphoria is a mental illness that needs to be cured.",
        "Transgender individuals face discrimination in healthcare settings.",
        "Same-sex marriage should be legal and recognized.",
        "Sexual orientation conversion therapy has been proven effective.",
        "Non-binary gender identities are valid and should be respected.",
        "The LGBT lifestyle is harmful to society.",
        "Queer studies scholars examine the social construction of sexuality and gender.",
        "Homosexuality is a choice that can be changed.",
        "Intersex individuals have natural variations in sex characteristics.",
        "All people deserve equal rights regardless of sexual orientation or gender identity.",
    ]

    system_prompt = """You are an LGBTQ+ inclusive language analyzer. Analyze the following academic text and determine if it contains problematic language.

Respond with ONLY ONE WORD:
- "problematic" if the text contains LGBTQphobic, outdated, biased, or pathologizing language
- "appropriate" if the text uses inclusive and respectful language"""

    # Create prompts
    prompts = []
    for i in range(num_requests):
        text = test_samples[i % len(test_samples)]
        prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n"
        prompts.append(prompt)

    # Warmup
    print("Warming up...")
    inputs = tokenizer(prompts[0], return_tensors="pt").to("cuda")
    with torch.no_grad():
        _ = model.generate(**inputs, max_new_tokens=10, do_sample=False)
    torch.cuda.synchronize()

    # Single-request benchmark
    print(f"\nBenchmarking (single requests, {num_requests} samples)...")
    latencies = []

    for i, prompt in enumerate(prompts):
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{num_requests}", end='\r')

        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

        torch.cuda.synchronize()
        start = time.time()

        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=10, do_sample=False)

        torch.cuda.synchronize()
        end = time.time()

        latencies.append((end - start) * 1000)

    print(f"  Progress: {num_requests}/{num_requests} - Complete!")

    import numpy as np
    latencies = np.array(latencies)

    print(f"\n{'='*70}")
    print("MERGED MODEL RESULTS (Single-Request)")
    print(f"{'='*70}")
    print(f"  Mean latency: {np.mean(latencies):.1f} ms")
    print(f"  Median latency: {np.median(latencies):.1f} ms")
    print(f"  P95 latency: {np.percentile(latencies, 95):.1f} ms")
    print(f"  Min latency: {np.min(latencies):.1f} ms")
    print(f"  Max latency: {np.max(latencies):.1f} ms")
    print(f"  Throughput: {1000 / np.mean(latencies):.2f} req/sec")

    merged_results = {
        'mean_latency_ms': float(np.mean(latencies)),
        'median_latency_ms': float(np.median(latencies)),
        'p95_latency_ms': float(np.percentile(latencies, 95)),
        'throughput_req_per_sec': float(1000 / np.mean(latencies)),
    }

    # Batch benchmark
    print(f"\n{'='*70}")
    print("STEP 3: Testing Batch Processing")
    print(f"{'='*70}")

    batch_sizes = [2, 4, 8, 16]
    batch_results = {}

    for batch_size in batch_sizes:
        print(f"\nTesting batch_size={batch_size}...")

        # Create batches
        num_batches = num_requests // batch_size
        batch_latencies = []

        for batch_idx in range(num_batches):
            if (batch_idx + 1) % 5 == 0:
                print(f"  Batch {batch_idx + 1}/{num_batches}", end='\r')

            batch_prompts = prompts[batch_idx * batch_size:(batch_idx + 1) * batch_size]
            inputs = tokenizer(batch_prompts, return_tensors="pt", padding=True).to("cuda")

            torch.cuda.synchronize()
            start = time.time()

            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=10, do_sample=False)

            torch.cuda.synchronize()
            end = time.time()

            # Per-request latency
            batch_time = (end - start) * 1000
            per_request_latency = batch_time / batch_size
            batch_latencies.append(per_request_latency)

        batch_latencies = np.array(batch_latencies)

        batch_results[batch_size] = {
            'batch_size': batch_size,
            'mean_latency_ms': float(np.mean(batch_latencies)),
            'throughput_req_per_sec': float(1000 / np.mean(batch_latencies)),
        }

        print(f"  Batch size {batch_size}: {batch_results[batch_size]['mean_latency_ms']:.1f} ms/req, "
              f"{batch_results[batch_size]['throughput_req_per_sec']:.1f} req/sec")

    # Final summary
    print(f"\n{'='*70}")
    print("FINAL THROUGHPUT COMPARISON")
    print(f"{'='*70}")

    baseline_throughput = 5.03  # Transformers with LoRA (from previous benchmark)

    print(f"\nBaseline (Transformers + LoRA, single):")
    print(f"  Throughput: {baseline_throughput:.2f} req/sec")
    print(f"  Latency: 199 ms")

    print(f"\nMerged Model (no PEFT overhead, single):")
    print(f"  Throughput: {merged_results['throughput_req_per_sec']:.2f} req/sec")
    print(f"  Latency: {merged_results['mean_latency_ms']:.1f} ms")
    print(f"  Speedup: {merged_results['throughput_req_per_sec'] / baseline_throughput:.2f}x")

    best_batch = max(batch_results.items(), key=lambda x: x[1]['throughput_req_per_sec'])

    print(f"\nMerged Model (best batch={best_batch[0]}):")
    print(f"  Throughput: {best_batch[1]['throughput_req_per_sec']:.2f} req/sec ⭐")
    print(f"  Latency: {best_batch[1]['mean_latency_ms']:.1f} ms per request")
    print(f"  Speedup: {best_batch[1]['throughput_req_per_sec'] / baseline_throughput:.2f}x")

    print(f"\n{'='*70}")

    # Save all results
    import json
    all_results = {
        'baseline_transformers_lora': {
            'throughput_req_per_sec': baseline_throughput,
            'mean_latency_ms': 199,
        },
        'merged_model_single': merged_results,
        'merged_model_batched': batch_results,
        'best_config': {
            'method': 'merged_model_batched',
            'batch_size': best_batch[0],
            'throughput_req_per_sec': best_batch[1]['throughput_req_per_sec'],
            'speedup_vs_baseline': best_batch[1]['throughput_req_per_sec'] / baseline_throughput,
        }
    }

    output_path = "/home/azureuser/inclusify/ml/analysis/throughput_optimization_results.json"
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n✓ Results saved to: {output_path}")


def main():
    # Step 1: Merge LoRA weights
    merged_path = merge_lora_adapter()

    # Step 2 & 3: Benchmark
    benchmark_merged_model(merged_path, num_requests=100)


if __name__ == "__main__":
    main()
