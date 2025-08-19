#!/usr/bin/env python3
"""
Pico W deployment script for Corvids Nest.

- Lists devices from deployment/device_index.json
- Lets you pick a device and a target Pico (via mpremote list)
- Merges deployment/common/network.json with the per-device device.json
- Copies bootstrap, shared modules, optional device app/, and config to the Pico

Requirements:
  - Python 3.8+
  - mpremote (pip install mpremote)

Usage:
  python deployment/scripts/deploy.py
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_DIR = REPO_ROOT / "deployment"
DEVICE_INDEX = DEPLOY_DIR / "device_index.json"
COMMON_NETWORK = DEPLOY_DIR / "common" / "network.json"
BOOTSTRAP_DIR = REPO_ROOT / "devices" / "bootstrap"
SHARED_DIR = REPO_ROOT / "shared"
DEVICES_ROOT = REPO_ROOT / "devices"

# MicroPython packages that must be present on the device (installed via mip)
REQUIRED_MIP_PACKAGES: list[str] = [
    "umqtt.simple",
    "onewire",
    "ds18x20",
]

# Reason: Simple utility functions to keep the main flow easy to follow.

def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def ensure_file_exists(path: Path, optional: bool = False) -> bool:
    if path.exists():
        return True
    if optional:
        return False
    print(f"ERROR: Missing required file: {path}")
    sys.exit(1)


def load_json(path: Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_device(devices: list[dict]) -> dict:
    print("Available devices:")
    for i, d in enumerate(devices):
        print(f"  [{i}] {d.get('device_id')}  -> {d.get('config')}  ({d.get('location','')})")
    while True:
        choice = input("Select device by number: ").strip()
        if choice.isdigit() and 0 <= int(choice) < len(devices):
            return devices[int(choice)]
        print("Invalid selection. Try again.")


def list_mpremote_ports() -> list[str]:
    try:
        p = run([sys.executable, "-m", "mpremote", "connect", "list"])
        ports = []
        for line in p.stdout.splitlines():
            # mpremote output example lines often contain the port at the end, e.g., '... COM5 ...'
            # We take the last token that looks like a port.
            tokens = line.split()
            for t in tokens:
                if t.upper().startswith("COM") or t.startswith("/dev/"):
                    ports.append(t)
        return sorted(set(ports))
    except Exception:
        return []


def select_port(ports: list[str]) -> str:
    if not ports:
        manual = input("No ports detected. Enter port (e.g., COM5 or /dev/ttyACM0): ").strip()
        return manual
    print("Detected Pico ports:")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p}")
    while True:
        choice = input("Select port by number: ").strip()
        if choice.isdigit() and 0 <= int(choice) < len(ports):
            return ports[int(choice)]
        print("Invalid selection. Try again.")


def merge_config(common_path: Path, device_path: Path) -> dict:
    merged: dict = {}
    if common_path.exists():
        common = load_json(common_path)
        if isinstance(common, dict):
            merged.update(common)
    if device_path.exists():
        dev = load_json(device_path)
        if isinstance(dev, dict):
            merged.update(dev)
    return merged


def mpremote_cp(port: str, src: Path, dst: str) -> None:
    cmd = [sys.executable, "-m", "mpremote", "connect", port, "cp", str(src), f":{dst}"]
    last_stdout = ""
    last_stderr = ""
    for attempt in range(3):
        p = run(cmd)
        last_stdout, last_stderr = p.stdout, p.stderr
        if p.returncode == 0:
            return
        # Reason: mpremote sometimes fails to enter raw REPL; a reset + small delay helps.
        if attempt == 0:
            print("mpremote cp failed; attempting reset and retry...")
            mpremote_reset(port)
            time.sleep(1.5)
        else:
            time.sleep(0.8)
    print(last_stdout)
    print(last_stderr)
    raise RuntimeError(f"mpremote cp failed for {src} -> {dst}")


def mpremote_cp_r(port: str, src_dir: Path, dst_dir: str) -> None:
    """
    Recursively copy a directory to the device by creating directories
    and copying files one-by-one, avoiding mpremote '-r' edge cases.

    Args:
        port (str): Serial port, e.g., 'COM3'.
        src_dir (Path): Local source directory.
        dst_dir (str): Device destination directory path (e.g., '/shared').
    """
    # Normalize destination to forward slashes and ensure leading '/'
    base_dst = dst_dir.replace("\\", "/")
    if not base_dst.startswith("/"):
        base_dst = "/" + base_dst
    # Create base destination directory
    mpremote_fs_mkdir(port, base_dst)
    for root, dirs, files in os.walk(src_dir):
        rel = Path(root).relative_to(src_dir)
        # Compute device dir path
        target_dir = Path(base_dst) / rel
        dev_dir = str(target_dir).replace("\\", "/")
        mpremote_fs_mkdir(port, dev_dir)
        for name in files:
            src_file = Path(root) / name
            dst_file = str((target_dir / name)).replace("\\", "/")
            mpremote_cp(port, src_file, dst_file)


def mpremote_fs_mkdir(port: str, path: str) -> None:
    cmd = [sys.executable, "-m", "mpremote", "connect", port, "fs", "mkdir", path]
    # Try twice; ignore error output on failure since dir may already exist
    for _ in range(2):
        p = run(cmd)
        if p.returncode == 0:
            return
        time.sleep(0.5)


def mpremote_mip_install(port: str, package: str, attempts: int = 2) -> None:
    """
    Install a MicroPython package on the device using mip.

    Args:
        port (str): Serial port (e.g., 'COM3').
        package (str): Package spec understood by mip (e.g., 'umqtt.simple').
        attempts (int): How many times to retry on transient failures.
    """
    cmd = [sys.executable, "-m", "mpremote", "connect", port, "mip", "install", package]
    last_stdout = ""
    last_stderr = ""
    for i in range(max(1, attempts)):
        p = run(cmd)
        last_stdout, last_stderr = p.stdout, p.stderr
        if p.returncode == 0:
            print(f"Installed with mip: {package}")
            return
        time.sleep(0.8)
    print(last_stdout)
    print(last_stderr)
    raise RuntimeError(f"mip install failed for package: {package}")


def mpremote_eval_imports(port: str, modules: list[str]) -> None:
    """
    Verify that a list of modules can be imported on the device. Raises on failure.

    Args:
        port (str): Serial port (e.g., 'COM3').
        modules (list[str]): Module names to import (e.g., 'umqtt.simple').
    """
    for mod in modules:
        # Use exec so we can run import statements; eval only accepts expressions.
        code = f"import {mod}\nprint('OK:{mod}')"
        p = run([sys.executable, "-m", "mpremote", "connect", port, "exec", code])
        if p.returncode != 0 or f"OK:{mod}" not in (p.stdout or ""):
            print(p.stdout)
            print(p.stderr)
            raise RuntimeError(f"Device import failed for module: {mod}")


def mpremote_reset(port: str) -> None:
    run([sys.executable, "-m", "mpremote", "connect", port, "reset"])


def mpremote_fs_rm(port: str, path: str) -> None:
    """
    Remove a file at the given path on the device (ignore errors if it doesn't exist
    or is a directory). This helps recover from a conflicting file occupying a
    directory name like '/shared' or '/app'.
    """
    run([sys.executable, "-m", "mpremote", "connect", port, "fs", "rm", path])


def main() -> None:
    ensure_file_exists(DEVICE_INDEX)
    devices_index = load_json(DEVICE_INDEX)
    devices = devices_index.get("devices", []) if isinstance(devices_index, dict) else []
    if not devices:
        print("No devices defined in deployment/device_index.json")
        sys.exit(1)

    selected = select_device(devices)
    device_id = selected.get("device_id")
    config_rel = selected.get("config")
    device_cfg_path = DEPLOY_DIR / str(config_rel)

    print(f"\nSelected: {device_id}")
    print(f"Device config: {device_cfg_path}")

    ports = list_mpremote_ports()
    port = select_port(ports)
    print(f"Using port: {port}\n")

    # Try to get the device into a clean state before filesystem ops
    print("Preparing device (reset)...")
    mpremote_reset(port)
    time.sleep(2.0)

    # Prepare filesystem
    mpremote_fs_mkdir(port, "/config")
    # Ensure clean directories for shared and app
    mpremote_fs_rm(port, "/shared")  # removes if a file exists; ignored if dir
    mpremote_fs_mkdir(port, "/shared")
    mpremote_fs_rm(port, "/app")     # removes if a file exists; ignored if dir
    mpremote_fs_mkdir(port, "/app")

    # Copy bootstrap files
    for name in ("main.py", "bootstrap_manager.py", "http_updater.py"):
        src = BOOTSTRAP_DIR / name
        ensure_file_exists(src)
        print(f"Copy {src} -> :/{name}")
        mpremote_cp(port, src, f"/{name}")

    # Copy shared package into /shared
    ensure_file_exists(SHARED_DIR)
    print(f"Copy {SHARED_DIR} -> :/shared")
    mpremote_cp_r(port, SHARED_DIR, "/shared")

    # Ensure vendor BMP3xx driver is placed in /lib as bmp3xx.py (per project requirement)
    bmp_driver = SHARED_DIR / "vendor" / "bmp3xx.py"
    ensure_file_exists(bmp_driver)  # required
    mpremote_fs_mkdir(port, "/lib")
    print(f"Copy {bmp_driver} -> :/lib/bmp3xx.py")
    mpremote_cp(port, bmp_driver, "/lib/bmp3xx.py")

    # Copy app for this device if present
    # We expect devices/<device_id with -/_ variants>/app
    # Normalize possible naming differences
    candidates = [
        DEVICES_ROOT / device_id.replace("-", "_") / "app",
        DEVICES_ROOT / device_id.replace("_", "-") / "app",
        DEVICES_ROOT / device_id / "app",
    ]
    app_dir = next((c for c in candidates if c.exists()), None)
    if app_dir:
        # Copy app directory into /app
        print(f"Copy {app_dir} -> :/app")
        mpremote_cp_r(port, app_dir, "/app")
    else:
        print("No device-specific app/ found. Leaving /app as-is.")

    # Ensure required MicroPython packages are installed
    if REQUIRED_MIP_PACKAGES:
        print("Installing MicroPython packages via mip...")
        for pkg in REQUIRED_MIP_PACKAGES:
            mpremote_mip_install(port, pkg)
        # Verify imports now to fail early if something's wrong
        mpremote_eval_imports(port, REQUIRED_MIP_PACKAGES)

    # Merge and push config
    merged = merge_config(COMMON_NETWORK, device_cfg_path)
    if not merged.get("device_id"):
        print("ERROR: Merged config missing device_id. Aborting.")
        sys.exit(1)

    tmp_out = REPO_ROOT / ".deploy_config_merged.json"
    with open(tmp_out, "w", encoding="utf-8") as f:
        json.dump(merged, f)
    print(f"Copy merged config -> :/config/device.json")
    mpremote_cp(port, tmp_out, "/config/device.json")
    try:
        tmp_out.unlink()
    except Exception:
        pass

    # Reset device
    print("Resetting device...")
    mpremote_reset(port)
    print("\nDone. Device should boot, connect, and publish boot/health topics.")


if __name__ == "__main__":
    main()
