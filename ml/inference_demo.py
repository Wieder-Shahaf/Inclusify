#!/usr/bin/env python3
"""
Inclusify Live Inference Demo
==============================

A lean command-line interface for demonstrating the LoRA-adapted model's
ability to classify sentences for LGBTQ+ inclusive language compliance.

Usage:
    python inference_demo.py                    # Interactive mode
    python inference_demo.py --sentence "..."   # Single sentence mode

Author: Generated for academic demonstration
"""

import argparse
import json
import re
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict

warnings.filterwarnings('ignore')

# Terminal colors for clear output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# Severity color mapping
SEVERITY_COLORS = {
    'Correct': Colors.GREEN,
    'Outdated': Colors.YELLOW,
    'Biased': Colors.YELLOW,
    'Potentially Offensive': Colors.RED,
    'Factually Incorrect': Colors.RED,
}


@dataclass
class InclusifyOutput:
    """Structured output from the model."""
    category: str
    severity: str
    explanation: str

    def to_dict(self) -> Dict:
        return {'category': self.category, 'severity': self.severity, 'explanation': self.explanation}


# System prompt for the model
SYSTEM_PROMPT = """You are an expert academic editor for the Inclusify project. Analyze sentences for LGBTQ+ inclusive language compliance.

OUTPUT REQUIREMENTS:
You MUST respond with ONLY a valid JSON object. No other text, no markdown, no explanation outside the JSON.

STRICT JSON SCHEMA:
{
  "category": "<rule category: e.g., 'N/A', 'Historical Pathologization', 'Identity Invalidation', 'Tone Policing', 'Medical Misinformation', 'False Causality', etc.>",
  "severity": "<EXACTLY one of: 'Correct', 'Outdated', 'Biased', 'Potentially Offensive', 'Factually Incorrect'>",
  "explanation": "<detailed reasoning for the classification>"
}

RULES:
- If the sentence is inclusive and appropriate, classify as "Correct" with category "N/A"
- Only classify as harmful if there is clear evidence of problematic language
- Provide specific, academic explanations"""


# Global model and tokenizer (loaded once at startup)
_model = None
_tokenizer = None
_device = None


def print_banner():
    """Print welcome banner."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}        INCLUSIFY - LGBTQ+ Inclusive Language Classifier{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}        LoRA-Adapted LLM Demo (Llama 3 8B + Custom Adapter){Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")


def load_model(adapter_path: str = "/home/azureuser/inclusify/ml/LoRA_Adapters"):
    """Load the model with LoRA adapter at startup with optimizations."""
    global _model, _tokenizer, _device

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    base_model_id = "lightblue/suzume-llama-3-8B-multilingual"

    print(f"{Colors.BLUE}Loading tokenizer...{Colors.END}")
    _tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    print(f"{Colors.BLUE}Loading base model ({base_model_id})...{Colors.END}")

    # Load with 4-bit quantization to save memory
    from transformers import BitsAndBytesConfig

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )

    # Try to use Flash Attention 2 if available, otherwise use SDPA (PyTorch native)
    try:
        import flash_attn
        attn_impl = "flash_attention_2"
        print(f"{Colors.GREEN}Flash Attention 2 available{Colors.END}")
    except ImportError:
        attn_impl = "sdpa"  # Scaled Dot Product Attention (PyTorch 2.0+ native, still fast)
        print(f"{Colors.YELLOW}Flash Attention 2 not installed, using SDPA (PyTorch native){Colors.END}")

    _model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        quantization_config=quantization_config,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation=attn_impl,
    )

    if Path(adapter_path).exists():
        print(f"{Colors.BLUE}Loading LoRA adapter from {adapter_path}...{Colors.END}")
        _model = PeftModel.from_pretrained(_model, adapter_path)
        print(f"{Colors.GREEN}LoRA adapter loaded successfully!{Colors.END}")
    else:
        print(f"{Colors.YELLOW}Warning: Adapter not found at {adapter_path}. Using base model.{Colors.END}")

    _model.eval()

    # Apply torch.compile for faster inference (PyTorch 2.0+)
    print(f"{Colors.BLUE}Compiling model with torch.compile()...{Colors.END}")
    try:
        _model = torch.compile(_model, mode="reduce-overhead")
        print(f"{Colors.GREEN}Model compiled successfully!{Colors.END}")
    except Exception as e:
        print(f"{Colors.YELLOW}torch.compile() not available: {e}{Colors.END}")

    _device = next(_model.parameters()).device

    print(f"{Colors.GREEN}Model ready on device: {_device}{Colors.END}")
    print(f"{Colors.GREEN}Optimizations: Flash Attention 2, torch.compile, 4-bit quantization{Colors.END}")
    return _model, _tokenizer


def parse_model_output(raw_output: str) -> Tuple[Optional[InclusifyOutput], Optional[str]]:
    """Parse the model's JSON output."""
    # Extract JSON from potential markdown code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_output)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        json_str = raw_output.strip()

    # Find JSON object boundaries
    start_idx = json_str.find('{')
    end_idx = json_str.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = json_str[start_idx:end_idx + 1]

    try:
        parsed = json.loads(json_str)
        return InclusifyOutput(
            category=parsed.get('category', 'N/A'),
            severity=parsed.get('severity', 'Correct'),
            explanation=parsed.get('explanation', 'No explanation provided.')
        ), None
    except json.JSONDecodeError as e:
        return None, f"JSON parsing error: {e}"


def predict(sentence: str) -> Tuple[str, Optional[InclusifyOutput], Optional[str], float]:
    """Generate prediction for a sentence. Returns (raw_output, parsed_output, error, inference_time_ms)."""
    import torch

    global _model, _tokenizer

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f'Analyze this sentence for LGBTQ+ inclusive language compliance:\n"{sentence}"'}
    ]

    input_ids = _tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to(_model.device)

    attention_mask = torch.ones_like(input_ids)

    terminators = [
        _tokenizer.eos_token_id,
        _tokenizer.convert_tokens_to_ids("<|eot_id|>")
    ]

    # Time the inference
    start_time = time.perf_counter()

    with torch.inference_mode():
        outputs = _model.generate(
            input_ids,
            attention_mask=attention_mask,
            max_new_tokens=128,  # Reduced from 256 - typical output is ~50-80 tokens
            eos_token_id=terminators,
            do_sample=False,
            pad_token_id=_tokenizer.eos_token_id,
            use_cache=True,  # Enable KV-cache for faster generation
        )

    end_time = time.perf_counter()
    inference_time_ms = (end_time - start_time) * 1000

    response = outputs[0][input_ids.shape[-1]:]
    raw_output = _tokenizer.decode(response, skip_special_tokens=True)

    parsed_output, error = parse_model_output(raw_output)
    return raw_output, parsed_output, error, inference_time_ms


def display_result(sentence: str, result: InclusifyOutput, inference_time_ms: float):
    """Display the classification result in a formatted way."""
    severity_color = SEVERITY_COLORS.get(result.severity, Colors.CYAN)

    print(f"\n{Colors.BOLD}{'─'*70}{Colors.END}")
    print(f"{Colors.BOLD}LoRA-Adapted Model{Colors.END}  |  Inference time: {Colors.CYAN}{inference_time_ms:.0f}ms{Colors.END}")
    print(f"{Colors.BOLD}{'─'*70}{Colors.END}")

    print(f"\n{Colors.BOLD}Input:{Colors.END}")
    print(f"  \"{sentence}\"")

    print(f"\n{Colors.BOLD}Classification:{Colors.END}")
    print(f"  {Colors.BOLD}Severity:{Colors.END}  {severity_color}{Colors.BOLD}{result.severity}{Colors.END}")
    print(f"  {Colors.BOLD}Category:{Colors.END}  {result.category}")

    print(f"\n{Colors.BOLD}Explanation:{Colors.END}")
    # Word wrap the explanation
    words = result.explanation.split()
    line = "  "
    for word in words:
        if len(line) + len(word) + 1 > 68:
            print(line)
            line = "  " + word
        else:
            line = line + " " + word if line.strip() else "  " + word
    if line.strip():
        print(line)

    print(f"\n{Colors.BOLD}{'─'*70}{Colors.END}")


def interactive_mode():
    """Run interactive inference mode."""
    print(f"\n{Colors.CYAN}Interactive Mode{Colors.END}")
    print(f"Enter sentences to classify. Type {Colors.BOLD}'quit'{Colors.END} or {Colors.BOLD}'exit'{Colors.END} to stop.")
    print(f"Type {Colors.BOLD}'examples'{Colors.END} to see sample sentences.\n")

    examples = [
        "Bisexual people are just promiscuous and cannot maintain committed relationships.",
        "Pansexuality refers to attraction regardless of gender.",
        "The push for LGBTQ+ rights is an attack on traditional family values.",
        "Gender identity is an individual's internal sense of being male, female, both, neither, or somewhere else along the gender spectrum.",
        "Homosexuality can be cured through therapy.",
    ]

    while True:
        try:
            sentence = input(f"\n{Colors.BOLD}Enter sentence:{Colors.END} ").strip()

            if sentence.lower() in ['quit', 'exit', 'q']:
                print(f"\n{Colors.CYAN}Thank you for using Inclusify!{Colors.END}\n")
                break

            if sentence.lower() == 'examples':
                print(f"\n{Colors.BOLD}Example sentences to try:{Colors.END}")
                for i, ex in enumerate(examples, 1):
                    print(f"  {i}. \"{ex[:60]}{'...' if len(ex) > 60 else ''}\"")
                continue

            if not sentence:
                continue

            print(f"\n{Colors.BLUE}Analyzing...{Colors.END}")

            raw, result, error, inference_time = predict(sentence)
            if result:
                display_result(sentence, result, inference_time)
            else:
                print(f"{Colors.RED}Error parsing output: {error}{Colors.END}")
                print(f"Raw output: {raw}")

        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}Interrupted. Goodbye!{Colors.END}\n")
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.END}")


def main():
    parser = argparse.ArgumentParser(
        description='Inclusify - LGBTQ+ Inclusive Language Classifier',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python inference_demo.py                          # Interactive mode
  python inference_demo.py -s "Your sentence here"  # Single sentence
        """
    )
    parser.add_argument('-s', '--sentence', type=str, help='Single sentence to classify')
    parser.add_argument('--adapter-path', type=str, default='/home/azureuser/inclusify/ml/LoRA_Adapters',
                       help='Path to LoRA adapter directory')

    args = parser.parse_args()

    print_banner()

    # Load model once at startup
    load_model(adapter_path=args.adapter_path)

    # Run inference
    if args.sentence:
        # Single sentence mode
        print(f"\n{Colors.BLUE}Analyzing sentence...{Colors.END}")
        raw, result, error, inference_time = predict(args.sentence)
        if result:
            display_result(args.sentence, result, inference_time)
        else:
            print(f"{Colors.RED}Error: {error}{Colors.END}")
    else:
        # Interactive mode
        interactive_mode()


if __name__ == '__main__':
    main()
