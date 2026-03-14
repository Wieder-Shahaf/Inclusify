#!/usr/bin/env python3
"""
Deploy Qwen2.5-3B with LoRA adapter on vLLM and benchmark throughput.
"""

import time
import asyncio
from typing import List
import numpy as np
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

def benchmark_vllm_throughput(
    model_name: str,
    adapter_path: str,
    batch_sizes: List[int] = [1, 4, 8, 16, 32],
    num_requests: int = 100,
):
    """Benchmark vLLM throughput with different batch sizes."""

    print("="*70)
    print("vLLM DEPLOYMENT & THROUGHPUT OPTIMIZATION")
    print("="*70)

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

    # Create full prompts
    prompts = []
    for i in range(num_requests):
        text = test_samples[i % len(test_samples)]
        prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n"
        prompts.append(prompt)

    # Sampling parameters
    sampling_params = SamplingParams(
        temperature=0.1,
        top_p=0.95,
        max_tokens=10,
        stop=["<|im_end|>"],
    )

    results = {}

    for max_num_seqs in batch_sizes:
        print(f"\n{'='*70}")
        print(f"Testing with max_num_seqs={max_num_seqs}")
        print(f"{'='*70}")

        try:
            # Initialize vLLM with different batch sizes
            print(f"Initializing vLLM (max_num_seqs={max_num_seqs})...")

            llm = LLM(
                model=model_name,
                enable_lora=True,
                max_lora_rank=64,
                max_num_seqs=max_num_seqs,
                gpu_memory_utilization=0.9,
                trust_remote_code=True,
                dtype="float16",
            )

            print("✓ vLLM initialized")

            # Create LoRA request
            lora_request = LoRARequest("inclusify", 1, adapter_path)

            # Warmup
            print("Warming up...")
            _ = llm.generate(
                prompts[:2],
                sampling_params,
                lora_request=lora_request,
            )

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
            mean_latency = (total_time / num_requests) * 1000  # ms

            # Calculate tokens
            total_input_tokens = sum(len(output.prompt_token_ids) for output in outputs)
            total_output_tokens = sum(len(output.outputs[0].token_ids) for output in outputs)

            input_throughput = total_input_tokens / total_time
            output_throughput = total_output_tokens / total_time
            total_token_throughput = (total_input_tokens + total_output_tokens) / total_time

            results[max_num_seqs] = {
                'max_num_seqs': max_num_seqs,
                'num_requests': num_requests,
                'total_time_s': total_time,
                'throughput_req_per_sec': throughput,
                'mean_latency_ms': mean_latency,
                'total_input_tokens': total_input_tokens,
                'total_output_tokens': total_output_tokens,
                'input_token_throughput': input_throughput,
                'output_token_throughput': output_throughput,
                'total_token_throughput': total_token_throughput,
            }

            print(f"\nResults:")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Throughput: {throughput:.2f} requests/sec")
            print(f"  Mean latency: {mean_latency:.1f} ms/request")
            print(f"  Input tokens/sec: {input_throughput:.1f}")
            print(f"  Output tokens/sec: {output_throughput:.1f}")
            print(f"  Total tokens/sec: {total_token_throughput:.1f}")

            # Clean up
            del llm
            import gc
            import torch
            gc.collect()
            torch.cuda.empty_cache()

        except Exception as e:
            print(f"✗ Failed with max_num_seqs={max_num_seqs}: {e}")
            import traceback
            traceback.print_exc()
            continue

    return results


def main():
    model_name = "Qwen/Qwen2.5-3B-Instruct"
    adapter_path = "/home/azureuser/inclusify/ml/adapters/qwen_r8_d0.2"

    print(f"\nModel: {model_name}")
    print(f"Adapter: {adapter_path}")

    # Test different batch sizes
    batch_sizes = [1, 4, 8, 16, 32]

    results = benchmark_vllm_throughput(
        model_name=model_name,
        adapter_path=adapter_path,
        batch_sizes=batch_sizes,
        num_requests=100,
    )

    # Find best configuration
    if results:
        print("\n" + "="*70)
        print("SUMMARY: Throughput Comparison")
        print("="*70)

        print(f"\n{'Batch Size':<12} {'Throughput':<20} {'Latency':<20} {'Tokens/sec':<15}")
        print("-" * 70)

        for batch_size, result in sorted(results.items()):
            print(f"{batch_size:<12} "
                  f"{result['throughput_req_per_sec']:<20.2f} "
                  f"{result['mean_latency_ms']:<20.1f} "
                  f"{result['total_token_throughput']:<15.1f}")

        # Best throughput
        best = max(results.items(), key=lambda x: x[1]['throughput_req_per_sec'])
        print(f"\n⭐ Best configuration: max_num_seqs={best[0]}")
        print(f"   Throughput: {best[1]['throughput_req_per_sec']:.2f} requests/sec")
        print(f"   Token throughput: {best[1]['total_token_throughput']:.1f} tokens/sec")

        # Save results
        import json
        output_path = "/home/azureuser/inclusify/ml/analysis/vllm_benchmark_results.json"
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Results saved to: {output_path}")

        # Compare with baseline
        baseline_throughput = 5.03  # from previous benchmark
        baseline_latency = 198.9

        print("\n" + "="*70)
        print("COMPARISON vs Standard Transformers")
        print("="*70)
        print(f"\nBaseline (Transformers):")
        print(f"  Throughput: {baseline_throughput:.2f} requests/sec")
        print(f"  Latency: {baseline_latency:.1f} ms")

        print(f"\nvLLM (best config):")
        print(f"  Throughput: {best[1]['throughput_req_per_sec']:.2f} requests/sec")
        print(f"  Latency: {best[1]['mean_latency_ms']:.1f} ms")

        speedup = best[1]['throughput_req_per_sec'] / baseline_throughput
        latency_improvement = baseline_latency / best[1]['mean_latency_ms']

        print(f"\nImprovement:")
        print(f"  Throughput: {speedup:.2f}x faster")
        print(f"  Latency: {latency_improvement:.2f}x better")

        print("\n" + "="*70)


if __name__ == "__main__":
    main()
