#!/usr/bin/env python3
"""
Switch the active LoRA adapter for the vLLM inference server.

Usage:
    # List available adapters
    python ml/scripts/switch_adapter.py --list

    # Switch to a specific adapter (updates active.json + patches vllm.service)
    python ml/scripts/switch_adapter.py --adapter qwen_r8_d0.2

    # Dry run (show what would change without applying)
    python ml/scripts/switch_adapter.py --adapter qwen_r8_d0.2 --dry-run

    # Run on the Azure VM (patches and restarts vllm.service)
    python ml/scripts/switch_adapter.py --adapter qwen_r8_d0.2 --restart-service

After running on the VM, verify with:
    curl http://localhost:8001/v1/models
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTERS_DIR = REPO_ROOT / "ml" / "adapters"
ACTIVE_JSON = ADAPTERS_DIR / "active.json"
VLLM_SERVICE_PATH = Path("/etc/systemd/system/vllm.service")


def list_adapters():
    adapters = []
    for d in sorted(ADAPTERS_DIR.iterdir()):
        if not d.is_dir():
            continue
        version_file = d / "version.json"
        if version_file.exists():
            with open(version_file) as f:
                meta = json.load(f)
            adapters.append((d.name, meta))
    return adapters


def get_active():
    if not ACTIVE_JSON.exists():
        return None
    with open(ACTIVE_JSON) as f:
        return json.load(f)


def set_active(adapter_name: str, dry_run: bool = False):
    adapter_dir = ADAPTERS_DIR / adapter_name
    if not adapter_dir.exists():
        print(f"ERROR: Adapter '{adapter_name}' not found in {ADAPTERS_DIR}")
        sys.exit(1)

    version_file = adapter_dir / "version.json"
    if not version_file.exists():
        print(f"ERROR: No version.json found in {adapter_dir}")
        sys.exit(1)

    with open(version_file) as f:
        meta = json.load(f)

    new_active = {
        "active_adapter": adapter_name,
        "version": meta["version"],
        "promoted_date": meta.get("training_date", "unknown"),
        "promoted_by": os.environ.get("USER", "unknown"),
        "notes": f"Switched via switch_adapter.py"
    }

    print(f"Switching active adapter to: {adapter_name} (v{meta['version']})")
    if dry_run:
        print("[DRY RUN] Would write to active.json:")
        print(json.dumps(new_active, indent=2))
    else:
        with open(ACTIVE_JSON, "w") as f:
            json.dump(new_active, f, indent=2)
        print(f"Updated {ACTIVE_JSON}")

    return adapter_name


def patch_vllm_service(adapter_name: str, dry_run: bool = False):
    if not VLLM_SERVICE_PATH.exists():
        print(f"WARNING: {VLLM_SERVICE_PATH} not found — skipping service patch")
        print("  (Run this script on the Azure VM to patch the service)")
        return

    with open(VLLM_SERVICE_PATH) as f:
        content = f.read()

    # Replace the lora-modules path — matches any adapter name
    new_content = re.sub(
        r"(--lora-modules inclusify=)([^\s\\]+)",
        lambda m: f"{m.group(1)}/home/azureuser/inclusify/ml/adapters/{adapter_name}",
        content
    )

    if new_content == content:
        print("WARNING: Could not find --lora-modules line in vllm.service")
        return

    if dry_run:
        print(f"[DRY RUN] Would patch {VLLM_SERVICE_PATH}:")
        for line in new_content.splitlines():
            if "lora-modules" in line:
                print(f"  {line.strip()}")
    else:
        with open(VLLM_SERVICE_PATH, "w") as f:
            f.write(new_content)
        print(f"Patched {VLLM_SERVICE_PATH}")


def restart_service(dry_run: bool = False):
    cmds = [
        ["sudo", "systemctl", "daemon-reload"],
        ["sudo", "systemctl", "restart", "vllm"],
    ]
    for cmd in cmds:
        if dry_run:
            print(f"[DRY RUN] Would run: {' '.join(cmd)}")
        else:
            print(f"Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
    if not dry_run:
        print("vLLM service restarted. Verify with: curl http://localhost:8001/v1/models")


def main():
    parser = argparse.ArgumentParser(description="Switch active LoRA adapter")
    parser.add_argument("--list", action="store_true", help="List available adapters")
    parser.add_argument("--adapter", help="Adapter name to switch to")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--restart-service", action="store_true",
                        help="Patch vllm.service and restart (run on Azure VM)")
    args = parser.parse_args()

    if args.list:
        adapters = list_adapters()
        active = get_active()
        active_name = active["active_adapter"] if active else None
        print(f"\nAvailable adapters in {ADAPTERS_DIR}:\n")
        for name, meta in adapters:
            marker = " ← ACTIVE" if name == active_name else ""
            print(f"  {name}{marker}")
            print(f"    version:  {meta['version']}")
            print(f"    accuracy: {meta.get('accuracy', 'N/A')}")
            print(f"    trained:  {meta.get('training_date', 'N/A')}")
            print(f"    notes:    {meta.get('notes', '')}")
            print()
        return

    if not args.adapter:
        parser.print_help()
        sys.exit(1)

    set_active(args.adapter, dry_run=args.dry_run)

    if args.restart_service:
        patch_vllm_service(args.adapter, dry_run=args.dry_run)
        restart_service(dry_run=args.dry_run)
    else:
        print("\nTo apply on the Azure VM, run:")
        print(f"  python ml/scripts/switch_adapter.py --adapter {args.adapter} --restart-service")


if __name__ == "__main__":
    main()
