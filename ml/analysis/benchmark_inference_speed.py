#!/usr/bin/env python3
"""
Benchmark inference speed for Qwen2.5-3B vs Qwen3.5-0.8B
"""

import time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import numpy as np

def benchmark_model(model_name, adapter_path, use_unsloth=False, num_samples=50):
    """Benchmark inference speed for a model."""

    print(f"\n{'='*70}")
    print(f"Benchmarking: {model_name}")
    print(f"{'='*70}")

    # Determine base model name
    if "Qwen2.5" in model_name:
        base_model_name = "Qwen/Qwen2.5-3B-Instruct"
    else:  # Qwen3.5
        base_model_name = "Qwen/Qwen3.5-0.8B"

    # Load model
    if use_unsloth:
        print("Loading with Unsloth...")
        from unsloth import FastLanguageModel

        base_model, _ = FastLanguageModel.from_pretrained(
            model_name=base_model_name,
            max_seq_length=2048,
            dtype=torch.float16,
            load_in_4bit=False,
        )
        tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
        model = PeftModel.from_pretrained(base_model, adapter_path)
    else:
        print("Loading with standard Transformers...")
        tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        model = PeftModel.from_pretrained(base_model, adapter_path)

    model.eval()
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

    # Extend to num_samples
    while len(test_samples) < num_samples:
        test_samples.extend(test_samples[:min(10, num_samples - len(test_samples))])
    test_samples = test_samples[:num_samples]

    system_prompt = """You are an LGBTQ+ inclusive language analyzer. Analyze the following academic text and determine if it contains problematic language.

Respond with ONLY ONE WORD:
- "problematic" if the text contains LGBTQphobic, outdated, biased, or pathologizing language
- "appropriate" if the text uses inclusive and respectful language"""

    # Warmup
    print("Warming up...")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": test_samples[0]}
    ]
    formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(formatted, return_tensors="pt", padding=True)
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}

    with torch.no_grad():
        _ = model.generate(**inputs, max_new_tokens=10, do_sample=False)

    if torch.cuda.is_available():
        torch.cuda.synchronize()

    # Benchmark
    print(f"Benchmarking {num_samples} samples...")
    latencies = []
    input_lengths = []
    output_lengths = []

    for i, text in enumerate(test_samples):
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{num_samples}", end='\r')

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(formatted, return_tensors="pt", padding=True)

        input_len = inputs['input_ids'].shape[1]
        input_lengths.append(input_len)

        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        # Measure inference time
        if torch.cuda.is_available():
            torch.cuda.synchronize()

        start = time.time()

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=10,
                temperature=0.1,
                do_sample=False,
            )

        if torch.cuda.is_available():
            torch.cuda.synchronize()

        end = time.time()

        latency = (end - start) * 1000  # Convert to ms
        latencies.append(latency)

        output_len = outputs.shape[1] - input_len
        output_lengths.append(output_len)

    print(f"  Progress: {num_samples}/{num_samples} - Complete!")

    # Calculate statistics
    latencies = np.array(latencies)
    input_lengths = np.array(input_lengths)
    output_lengths = np.array(output_lengths)

    results = {
        'model': model_name,
        'num_samples': num_samples,
        'mean_latency_ms': float(np.mean(latencies)),
        'median_latency_ms': float(np.median(latencies)),
        'std_latency_ms': float(np.std(latencies)),
        'min_latency_ms': float(np.min(latencies)),
        'max_latency_ms': float(np.max(latencies)),
        'p95_latency_ms': float(np.percentile(latencies, 95)),
        'p99_latency_ms': float(np.percentile(latencies, 99)),
        'mean_input_tokens': float(np.mean(input_lengths)),
        'mean_output_tokens': float(np.mean(output_lengths)),
        'throughput_samples_per_sec': 1000.0 / np.mean(latencies),
    }

    # Print results
    print(f"\n{'='*70}")
    print(f"Results for {model_name}:")
    print(f"{'='*70}")
    print(f"  Samples processed: {num_samples}")
    print(f"  Mean latency: {results['mean_latency_ms']:.1f} ms/sample")
    print(f"  Median latency: {results['median_latency_ms']:.1f} ms/sample")
    print(f"  P95 latency: {results['p95_latency_ms']:.1f} ms/sample")
    print(f"  P99 latency: {results['p99_latency_ms']:.1f} ms/sample")
    print(f"  Min latency: {results['min_latency_ms']:.1f} ms/sample")
    print(f"  Max latency: {results['max_latency_ms']:.1f} ms/sample")
    print(f"  Throughput: {results['throughput_samples_per_sec']:.2f} samples/sec")
    print(f"  Avg input tokens: {results['mean_input_tokens']:.1f}")
    print(f"  Avg output tokens: {results['mean_output_tokens']:.1f}")
    print(f"{'='*70}")

    # Clean up
    del model, base_model, tokenizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return results


def main():
    print("="*70)
    print("INFERENCE SPEED BENCHMARK")
    print("Qwen2.5-3B vs Qwen3.5-0.8B")
    print("="*70)

    # Check GPU
    if torch.cuda.is_available():
        print(f"\nGPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA Version: {torch.version.cuda}")
    else:
        print("\n⚠️  Running on CPU (will be very slow)")

    num_samples = 50

    # Benchmark Qwen2.5-3B
    qwen25_results = benchmark_model(
        model_name="Qwen2.5-3B",
        adapter_path="/home/azureuser/inclusify/ml/adapters/qwen_r8_d0.2",
        use_unsloth=False,
        num_samples=num_samples
    )

    # Benchmark Qwen3.5-0.8B
    qwen3_results = benchmark_model(
        model_name="Qwen3.5-0.8B",
        adapter_path="/home/azureuser/inclusify/ml/adapters/qwen3/qwen3_r32_d0.05/checkpoint-150",
        use_unsloth=True,
        num_samples=num_samples
    )

    # Comparison
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)

    speedup = qwen25_results['mean_latency_ms'] / qwen3_results['mean_latency_ms']

    print(f"\nLatency (lower is better):")
    print(f"  Qwen2.5-3B: {qwen25_results['mean_latency_ms']:.1f} ms/sample")
    print(f"  Qwen3.5-0.8B: {qwen3_results['mean_latency_ms']:.1f} ms/sample")
    print(f"  {'Qwen3.5 is ' + f'{speedup:.2f}x FASTER' if speedup > 1 else 'Qwen2.5 is ' + f'{1/speedup:.2f}x FASTER'}")

    print(f"\nThroughput (higher is better):")
    print(f"  Qwen2.5-3B: {qwen25_results['throughput_samples_per_sec']:.2f} samples/sec")
    print(f"  Qwen3.5-0.8B: {qwen3_results['throughput_samples_per_sec']:.2f} samples/sec")

    print(f"\nP95 Latency (95% of requests faster than):")
    print(f"  Qwen2.5-3B: {qwen25_results['p95_latency_ms']:.1f} ms")
    print(f"  Qwen3.5-0.8B: {qwen3_results['p95_latency_ms']:.1f} ms")

    print("\n" + "="*70)

    # Save results
    import json
    results = {
        'qwen25': qwen25_results,
        'qwen3': qwen3_results,
        'speedup': float(speedup),
    }

    output_path = "/home/azureuser/inclusify/ml/analysis/inference_benchmark_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Results saved to: {output_path}")


if __name__ == "__main__":
    main()
