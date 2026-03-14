#!/usr/bin/env python3
"""
Optimize inference throughput for Qwen2.5-3B with batch processing.
No disk writes needed - benchmarks in-memory only.
"""

import time
import torch
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def benchmark_with_optimizations(num_requests=100):
    """Benchmark different optimization strategies."""

    print("="*70)
    print("THROUGHPUT OPTIMIZATION: Qwen2.5-3B + LoRA")
    print("="*70)

    # Load model
    print("\nLoading model with LoRA adapter...")
    base_model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-3B-Instruct",
        torch_dtype=torch.float16,
        device_map="auto",
    )

    model = PeftModel.from_pretrained(
        base_model,
        "/home/azureuser/inclusify/ml/adapters/qwen_r8_d0.2"
    )
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct")
    print("✓ Model loaded")

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

    results = {}

    # ========================================
    # Test 1: Baseline (current performance)
    # ========================================
    print(f"\n{'='*70}")
    print("[TEST 1] Baseline: Single requests, no optimizations")
    print(f"{'='*70}")

    latencies = []
    for i, prompt in enumerate(prompts[:50]):  # Use 50 for speed
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/50", end='\r')

        inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True).to("cuda")

        torch.cuda.synchronize()
        start = time.time()

        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=10, do_sample=False)

        torch.cuda.synchronize()
        end = time.time()

        latencies.append((end - start) * 1000)

    baseline_latency = np.mean(latencies)
    baseline_throughput = 1000 / baseline_latency

    results['baseline'] = {
        'mean_latency_ms': float(baseline_latency),
        'throughput_req_per_sec': float(baseline_throughput),
    }

    print(f"\n  Mean latency: {baseline_latency:.1f} ms")
    print(f"  Throughput: {baseline_throughput:.2f} req/sec")

    # ========================================
    # Test 2: Batch Processing
    # ========================================
    print(f"\n{'='*70}")
    print("[TEST 2] Batch Processing (different batch sizes)")
    print(f"{'='*70}")

    batch_configs = [2, 4, 8, 16]
    batch_results = {}

    for batch_size in batch_configs:
        print(f"\n  Testing batch_size={batch_size}...")

        num_batches = 50 // batch_size
        batch_latencies = []

        for batch_idx in range(num_batches):
            batch_prompts = prompts[batch_idx * batch_size:(batch_idx + 1) * batch_size]
            inputs = tokenizer(
                batch_prompts,
                return_tensors="pt",
                padding=True,
                max_length=512,
                truncation=True
            ).to("cuda")

            torch.cuda.synchronize()
            start = time.time()

            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=10, do_sample=False)

            torch.cuda.synchronize()
            end = time.time()

            # Average per-request latency in the batch
            batch_time = (end - start) * 1000
            per_request_latency = batch_time / batch_size
            batch_latencies.append(per_request_latency)

        mean_latency = np.mean(batch_latencies)
        throughput = 1000 / mean_latency

        batch_results[batch_size] = {
            'batch_size': batch_size,
            'mean_latency_ms': float(mean_latency),
            'throughput_req_per_sec': float(throughput),
            'speedup_vs_baseline': float(throughput / baseline_throughput),
        }

        print(f"    Latency: {mean_latency:.1f} ms/req")
        print(f"    Throughput: {throughput:.1f} req/sec")
        print(f"    Speedup: {throughput / baseline_throughput:.2f}x")

    results['batched'] = batch_results

    # ========================================
    # Test 3: With KV Cache
    # ========================================
    print(f"\n{'='*70}")
    print("[TEST 3] With use_cache=True (KV cache)")
    print(f"{'='*70}")

    # Most efficient batch size from previous test
    best_batch_size = max(batch_results.items(), key=lambda x: x[1]['throughput_req_per_sec'])[0]

    num_batches = 50 // best_batch_size
    kv_cache_latencies = []

    for batch_idx in range(num_batches):
        if (batch_idx + 1) % 3 == 0:
            print(f"  Batch {batch_idx + 1}/{num_batches}", end='\r')

        batch_prompts = prompts[batch_idx * best_batch_size:(batch_idx + 1) * best_batch_size]
        inputs = tokenizer(
            batch_prompts,
            return_tensors="pt",
            padding=True,
            max_length=512,
            truncation=True
        ).to("cuda")

        torch.cuda.synchronize()
        start = time.time()

        with torch.no_grad():
            # Enable KV cache explicitly
            model.config.use_cache = True
            outputs = model.generate(**inputs, max_new_tokens=10, do_sample=False, use_cache=True)

        torch.cuda.synchronize()
        end = time.time()

        batch_time = (end - start) * 1000
        per_request_latency = batch_time / best_batch_size
        kv_cache_latencies.append(per_request_latency)

    kv_latency = np.mean(kv_cache_latencies)
    kv_throughput = 1000 / kv_latency

    results['kv_cache_batched'] = {
        'batch_size': best_batch_size,
        'mean_latency_ms': float(kv_latency),
        'throughput_req_per_sec': float(kv_throughput),
        'speedup_vs_baseline': float(kv_throughput / baseline_throughput),
    }

    print(f"\n  Batch size: {best_batch_size}")
    print(f"  Latency: {kv_latency:.1f} ms/req")
    print(f"  Throughput: {kv_throughput:.1f} req/sec")
    print(f"  Speedup: {kv_throughput / baseline_throughput:.2f}x")

    # ========================================
    # Final Summary
    # ========================================
    print(f"\n{'='*70}")
    print("OPTIMIZATION SUMMARY")
    print(f"{'='*70}")

    print(f"\n{'Configuration':<35} {'Throughput':<15} {'Speedup':<10}")
    print("-" * 70)

    print(f"{'Baseline (single, with LoRA)':<35} "
          f"{baseline_throughput:<15.2f} "
          f"{'1.00x':<10}")

    for batch_size, data in sorted(batch_results.items()):
        print(f"{'Batch size ' + str(batch_size):<35} "
              f"{data['throughput_req_per_sec']:<15.2f} "
              f"{data['speedup_vs_baseline']:.2f}x")

    print(f"{'KV Cache + Batch ' + str(best_batch_size):<35} "
          f"{kv_throughput:<15.2f} "
          f"{kv_throughput / baseline_throughput:.2f}x")

    # Best configuration
    best_method = max(
        [('baseline', baseline_throughput)]
        + [(f'batch_{k}', v['throughput_req_per_sec']) for k, v in batch_results.items()]
        + [('kv_cache', kv_throughput)],
        key=lambda x: x[1]
    )

    print(f"\n⭐ Best Configuration: {best_method[0]}")
    print(f"   Throughput: {best_method[1]:.2f} req/sec")
    print(f"   Speedup: {best_method[1] / baseline_throughput:.2f}x vs baseline")

    # Save results
    import json
    output_path = "/home/azureuser/inclusify/ml/analysis/throughput_optimization_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Results saved to: {output_path}")
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    benchmark_with_optimizations()
