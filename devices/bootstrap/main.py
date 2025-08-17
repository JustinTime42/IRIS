"""
Bootstrap entry point for Pico W.

Runs the immortal bootstrap loop and never updates itself.

This file is flashed once and should never be modified by OTA updates.

Google-style docstrings are used throughout.
"""
# Reason: Keep `main.py` tiny and resilient; all logic lives in `bootstrap_manager.py`.

try:
    from .bootstrap_manager import BootstrapManager
except ImportError:
    # When frozen or copied to root on device, relative import may fail
    try:
        from bootstrap_manager import BootstrapManager  # type: ignore
    except Exception as e:  # Final fallback: log and halt in a safe loop
        import sys
        sys.print_exception(e)
        while True:
            # Minimal infinite loop to avoid watchdog resets without thrashing
            pass

# Optional config manager
try:
    from shared.config_manager import load_device_config
except Exception:
    load_device_config = None  # type: ignore


def main():
    """
    Initialize and run the bootstrap manager forever.

    Returns:
        None: This function never returns by design.
    """
    # Load device configuration if available
    cfg = {
        "device_id": "device-unknown",
        "wifi_ssid": "",
        "wifi_password": "",
        "mqtt_host": "",
        "mqtt_port": 1883,
    }
    try:
        if load_device_config:
            loaded = load_device_config()
            if isinstance(loaded, dict):
                cfg.update(loaded)
    except Exception:
        # Proceed with defaults; bootstrap will SOS about missing config
        pass

    bm = BootstrapManager(
        device_id=str(cfg.get("device_id") or "device-unknown"),
        wifi_ssid=str(cfg.get("wifi_ssid") or ""),
        wifi_password=str(cfg.get("wifi_password") or ""),
        mqtt_host=str(cfg.get("mqtt_host") or ""),
        mqtt_port=int(cfg.get("mqtt_port") or 1883),
    )
    bm.run_forever()


if __name__ == "__main__":
    main()
