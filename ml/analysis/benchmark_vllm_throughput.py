#!/usr/bin/env python3
"""
Comprehensive vLLM throughput benchmark with different configurations.
"""

import time
import os
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest
import numpy as np
import json

# Set environment for compatibility
os.environ['VLLM_ATTENTION_BACKEND'] = 'XFORMERS'

def benchmark_configuration(max_num_seqs, num_requests=100):
    """Benchmark a specific vLLM configuration."""

    print(f"\n{'='*70}")
    print(f"Testing: max_num_seqs={max_num_seqs}")
    print(f"{'='*70}")

    # Initialize vLLM
    print(f"Initializing vLLM...")
    llm = LLM(
        model="Qwen/Qwen2.5-3B-Instruct",
        enable_lora=True,
        max_lora_rank=16,
        max_num_seqs=max_num_seqs,
        gpu_memory_utilization=0.9,
        trust_remote_code=True,
        dtype="float16",
        enforce_eager=False,
    )

    # LoRA request
    lora_request = LoRARequest(
        lora_name="inclusify",
        lora_int_id=1,
        lora_local_path="/home/azureuser/inclusify/ml/adapters/qwen_r8_d0.2"
    )

    # Sampling params
    sampling_params = SamplingParams(
        temperature=0.1,
        max_tokens=10,
        stop=["<|im_end|>"],
    )

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
    _ = llm.generate(prompts[:2], sampling_params, lora_request=lora_request)

    # Benchmark
    print(f"Benchmarking {num_requests} requests...")
    start = time.time()

    outputs = llm.generate(
        prompts,
        sampling_params,
        lora_request=lora_request,
    )

    end = time.time()

    # Calculate metrics
    total_time = end - start
    throughput = num_requests / total_time
    mean_latency = (total_time / num_requests) * 1000

    # Token metrics
    total_input_tokens = sum(len(output.prompt_token_ids) for output in outputs)
    total_output_tokens = sum(len(output.outputs[0].token_ids) for output in outputs)
    token_throughput = (total_input_tokens + total_output_tokens) / total_time

    results = {
        'max_num_seqs': max_num_seqs,
        'num_requests': num_requests,
        'total_time_s': total_time,
        'throughput_req_per_sec': throughput,
        'mean_latency_ms': mean_latency,
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'token_throughput': token_throughput,
    }

    print(f"\nResults:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Throughput: {throughput:.2f} requests/sec ⭐")
    print(f"  Mean latency: {mean_latency:.1f} ms/request")
    print(f"  Token throughput: {token_throughput:.1f} tokens/sec")
    print(f"  Input tokens: {total_input_tokens}")
    print(f"  Output tokens: {total_output_tokens}")

    # Clean up
    del llm
    import gc, torch
    gc.collect()
    torch.cuda.empty_cache()

    return results


def main():
    print("="*70)
    print("vLLM THROUGHPUT OPTIMIZATION BENCHMARK")
    print("Model: Qwen2.5-3B + LoRA")
    print("="*70)

    # Test different max_num_seqs (batch sizes)
    configurations = [4, 8, 16, 32, 64]
    all_results = {}

    for config in configurations:
        try:
            result = benchmark_configuration(config, num_requests=100)
            all_results[config] = result
        except Exception as e:
            print(f"\n✗ Failed with max_num_seqs={config}: {e}")
            continue

    # Summary
    if not all_results:
        print("\n❌ All configurations failed!")
        return

    print(f"\n{'='*70}")
    print("SUMMARY: vLLM Throughput Optimization")
    print(f"{'='*70}")

    print(f"\n{'max_num_seqs':<15} {'Throughput':<20} {'Latency':<15}")
    print("-" * 70)

    for config, result in sorted(all_results.items()):
        print(f"{config:<15} "
              f"{result['throughput_req_per_sec']:<20.2f} "
              f"{result['mean_latency_ms']:<15.1f}")

    # Best configuration
    best = max(all_results.items(), key=lambda x: x[1]['throughput_req_per_sec'])

    print(f"\n⭐ BEST Configuration: max_num_seqs={best[0]}")
    print(f"   Throughput: {best[1]['throughput_req_per_sec']:.2f} requests/sec")
    print(f"   Latency: {best[1]['mean_latency_ms']:.1f} ms/request")
    print(f"   Token throughput: {best[1]['token_throughput']:.1f} tokens/sec")

    # Compare with baseline
    baseline_throughput = 4.49  # Manual batching baseline
    baseline_batch16_throughput = 13.35  # Manual batch=16

    print(f"\n{'='*70}")
    print("COMPARISON")
    print(f"{'='*70}")

    print(f"\nTransformers (single request): 4.49 req/sec")
    print(f"Transformers (manual batch 16): 13.35 req/sec")
    print(f"vLLM (best config): {best[1]['throughput_req_per_sec']:.2f} req/sec")

    speedup_vs_single = best[1]['throughput_req_per_sec'] / baseline_throughput
    speedup_vs_batch = best[1]['throughput_req_per_sec'] / baseline_batch16_throughput

    print(f"\nSpeedup:")
    print(f"  vs Single: {speedup_vs_single:.2f}x")
    print(f"  vs Manual Batch 16: {speedup_vs_batch:.2f}x")

    print(f"\n{'='*70}")

    # Save results
    output_path = "/home/azureuser/inclusify/ml/analysis/vllm_throughput_results.json"
    with open(output_path, 'w') as f:
        json.dump({
            'configurations': all_results,
            'best_config': best[0],
            'best_throughput': best[1]['throughput_req_per_sec'],
            'baseline_single': baseline_throughput,
            'baseline_batch16': baseline_batch16_throughput,
            'speedup_vs_single': speedup_vs_single,
            'speedup_vs_batch16': speedup_vs_batch,
        }, f, indent=2)

    print(f"\n✓ Results saved to: {output_path}\n")


if __name__ == "__main__":
    main()
