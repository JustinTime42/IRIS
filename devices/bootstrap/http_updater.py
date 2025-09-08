"""
HTTP updater for OTA application updates on Pico W.

Uses HTTP to fetch application files and write them to the filesystem.
Never modifies bootstrap files.
"""
# Reason: Provide a minimal and safe OTA mechanism; robust logic added iteratively.

try:
    import urequests as requests  # MicroPython HTTP client
except ImportError:
    # Allow running on CPython for linting/simulation without network
    import sys
    requests = None  # type: ignore
try:
    import uhashlib as hashlib  # type: ignore
except Exception:
    try:
        import hashlib  # type: ignore
    except Exception:
        hashlib = None  # type: ignore

import os

CHUNK_SIZE = 1024  # bytes per read; tuned for Pico W RAM profile
MAX_RETRIES = 2    # per-file download retries


class HttpUpdater:
    """
    Minimal HTTP updater that downloads and applies update payloads.

    Methods assume a payload format like:
        {
            "files": [
                {"url": "https://.../raw/path/app/main.py", "path": "app/main.py"},
                {"url": "https://.../raw/path/app/utils.py", "path": "app/utils.py"}
            ]
        }
    Bootstrap directory paths are ignored to protect the immortal layer.
    """

    BOOTSTRAP_PREFIXES = ("bootstrap/", "/bootstrap/", "devices/bootstrap/")

    def download_and_apply(self, payload: dict) -> None:
        """
        Download and write files from the update payload.

        Args:
            payload (dict): Manifest with file descriptors.
        """
        files = (payload or {}).get("files", [])
        if not isinstance(files, list):
            raise ValueError("Invalid payload: files must be a list")

        for f in files:
            url = f.get("url")
            path = f.get("path")
            size = f.get("size")  # optional
            sha256 = f.get("sha256")  # optional hex digest
            if not url or not path:
                raise ValueError("Invalid file descriptor: missing url or path")
            if self._is_bootstrap_path(path):
                # Skip any attempt to modify bootstrap layer
                continue
            # Simple retry loop per file
            last_err = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    self._download_to_path(url, path, expected_size=size, expected_sha256=sha256)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    # Best-effort small delay without importing time (may not exist on CPython path)
                    try:
                        import time as _t
                        _t.sleep(0.2)
                    except Exception:
                        pass
            if last_err is not None:
                raise last_err

    # ------------------------------------------------------------------
    def _is_bootstrap_path(self, path: str) -> bool:
        """
        Check if a target path would affect the bootstrap layer.

        Args:
            path (str): Filesystem path relative to device root.

        Returns:
            bool: True if path appears to target bootstrap files.
        """
        p = path.replace("\\", "/").lstrip("/")
        for prefix in self.BOOTSTRAP_PREFIXES:
            if p.startswith(prefix):
                return True
        # Protect top-level bootstrap files by exact name
        if p in ("main.py", "bootstrap_manager.py", "http_updater.py"):
            return True
        return False

    def _download_to_path(self, url: str, path: str, expected_size=None, expected_sha256=None) -> None:
        """
        Download file bytes from URL and save to the given path.

        Args:
            url (str): HTTP(S) URL to fetch.
            path (str): Relative path to write on device.
            expected_size (int|None): Optional size for validation.
            expected_sha256 (str|None): Optional lowercase hex digest for validation.
        """
        if requests is None:
            # In non-MicroPython context, create placeholder file
            self._ensure_parent_dir(path)
            with open(path, "wb") as fp:
                fp.write(b"# placeholder written without network\n")
            return

        resp = requests.get(url, stream=True)  # type: ignore
        hasher = None
        if expected_sha256 and hashlib:
            try:
                hasher = hashlib.sha256()  # type: ignore[attr-defined]
            except Exception:
                hasher = None
        bytes_written = 0
        tmp_path = path + ".new"
        try:
            if resp.status_code != 200:
                raise OSError("HTTP error {} for {}".format(resp.status_code, url))
            self._ensure_parent_dir(path)
            # Stream to temporary file to improve power-failure safety
            with open(tmp_path, "wb") as fp:
                # Prefer raw reads if available
                raw = getattr(resp, "raw", None)
                if raw and hasattr(raw, "read"):
                    while True:
                        buf = raw.read(CHUNK_SIZE)  # type: ignore
                        if not buf:
                            break
                        fp.write(buf)
                        bytes_written += len(buf)
                        if hasher:
                            try:
                                hasher.update(buf)  # type: ignore
                            except Exception:
                                hasher = None
                else:
                    # Fallback: read from resp.content in one shot (may be memory heavy)
                    content = resp.content
                    fp.write(content)
                    bytes_written += len(content)
                    if hasher:
                        try:
                            hasher.update(content)  # type: ignore
                        except Exception:
                            hasher = None
                try:
                    fp.flush()
                except Exception:
                    pass
            # Validate size if provided
            try:
                if expected_size is not None:
                    if int(expected_size) != int(bytes_written):
                        raise OSError("size_mismatch for {}: got {} expected {}".format(path, bytes_written, expected_size))
            except Exception:
                # If validation type casting fails, treat as mismatch
                raise
            # Validate hash if provided
            if expected_sha256 and hasher:
                try:
                    digest = hasher.hexdigest()
                except Exception:
                    digest = None
                if not digest or digest.lower() != str(expected_sha256).lower():
                    raise OSError("sha256_mismatch for {}".format(path))
            # Atomic-ish move into place
            try:
                # Remove existing file first if rename would fail on some FS variants
                if self._exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                os.rename(tmp_path, path)
            finally:
                # If rename failed, try to clean temp to avoid clutter; ignore errors
                if self._exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
        finally:
            try:
                resp.close()
            except Exception:
                pass

    def _ensure_parent_dir(self, path: str) -> None:
        """
        Create parent directories if missing.

        Args:
            path (str): Target file path.
        """
        norm = path.replace("\\", "/")
        d = norm.rsplit("/", 1)[0] if "/" in norm else ""
        if d and not self._exists(d):
            self._makedirs(d)

    # Minimal directory helpers that work on MicroPython and CPython
    def _exists(self, p: str) -> bool:
        try:
            st = os.stat(p)
            return bool(st)
        except Exception:
            return False

    def _makedirs(self, d: str) -> None:
        parts = []
        for segment in d.replace("\\", "/").split("/"):
            parts.append(segment)
            cur = "/".join(parts)
            if not cur:
                continue
            try:
                os.mkdir(cur)
            except OSError:
                # Already exists or cannot create; continue best-effort
                pass
