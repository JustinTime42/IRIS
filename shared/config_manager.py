"""
Configuration manager for device identity, WiFi, and MQTT settings.

Stores and loads config from /config/device.json on the device filesystem.
Implements safe atomic writes and basic schema validation.
"""
# Reason: Centralize secrets and identity outside of immortal bootstrap code.

try:
    import ujson as json  # type: ignore
except Exception:
    import json  # type: ignore

import os

try:
    import ubinascii  # type: ignore
except Exception:
    ubinascii = None  # type: ignore

try:
    import machine  # type: ignore
except Exception:
    machine = None  # type: ignore

DEFAULT_PATH = "/config/device.json"


def _default_device_id() -> str:
    """
    Build a fallback device_id using the MCU unique id when available.

    Returns:
        str: Reasonable default device id.
    """
    if machine and hasattr(machine, "unique_id"):
        try:
            raw = machine.unique_id()
            if ubinascii:
                return ubinascii.hexlify(raw).decode()
            return str(raw)
        except Exception:
            pass
    return "device-unknown"


def load_device_config(path: str = DEFAULT_PATH) -> dict:
    """
    Load and validate the device configuration.

    Args:
        path (str): Filesystem path to the JSON config.

    Returns:
        dict: Configuration dict with keys:
            device_id (str)
            wifi_ssid (str | None)
            wifi_password (str | None)
            mqtt_host (str | None)
            mqtt_port (int)
    """
    cfg = {
        "device_id": _default_device_id(),
        "wifi_ssid": None,
        "wifi_password": None,
        "mqtt_host": None,
        "mqtt_port": 1883,
    }
    try:
        with open(path, "rb") as fp:
            data = fp.read()
        file_cfg = json.loads(data)
        if isinstance(file_cfg, dict):
            cfg.update(file_cfg)
    except Exception:
        # Missing or invalid file: return defaults; caller may emit SOS
        return cfg

    # Normalize and validate types
    if not isinstance(cfg.get("device_id"), str) or not cfg.get("device_id"):
        cfg["device_id"] = _default_device_id()
    if not isinstance(cfg.get("mqtt_port"), int):
        cfg["mqtt_port"] = 1883

    # Ensure absent or empty strings become None for optional fields
    for k in ("wifi_ssid", "wifi_password", "mqtt_host"):
        v = cfg.get(k)
        if not isinstance(v, str) or not v:
            cfg[k] = None

    return cfg


def save_device_config(cfg: dict, path: str = DEFAULT_PATH) -> None:
    """
    Save configuration atomically to prevent corruption on power loss.

    Args:
        cfg (dict): Configuration dictionary.
        path (str): Target file path.
    """
    # Ensure parent directory exists
    directory = path.rsplit("/", 1)[0] if "/" in path else ""
    if directory and not _exists(directory):
        _makedirs(directory)

    tmp = path + ".tmp"
    data = json.dumps(cfg)
    with open(tmp, "wb") as fp:
        fp.write(data.encode())
        try:
            # Some ports support flush+fsync; ignore if not available
            fp.flush()
            if hasattr(os, "fsync"):
                os.fsync(fp.fileno())
        except Exception:
            pass
    try:
        if hasattr(os, "rename"):
            os.rename(tmp, path)
        else:
            # Fallback: remove then write final (not atomic but best-effort)
            try:
                os.remove(path)
            except Exception:
                pass
            with open(path, "wb") as fp2:
                fp2.write(data.encode())
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


def _exists(p: str) -> bool:
    try:
        os.stat(p)
        return True
    except Exception:
        return False


def _makedirs(d: str) -> None:
    parts = []
    for segment in d.replace("\\", "/").split("/"):
        if not segment:
            continue
        parts.append(segment)
        cur = "/".join(parts)
        try:
            os.mkdir(cur)
        except Exception:
            # Already exists or cannot create; continue
            pass
