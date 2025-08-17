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

import os


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
            if not url or not path:
                raise ValueError("Invalid file descriptor: missing url or path")
            if self._is_bootstrap_path(path):
                # Skip any attempt to modify bootstrap layer
                continue
            self._download_to_path(url, path)

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

    def _download_to_path(self, url: str, path: str) -> None:
        """
        Download file bytes from URL and save to the given path.

        Args:
            url (str): HTTP(S) URL to fetch.
            path (str): Relative path to write on device.
        """
        if requests is None:
            # In non-MicroPython context, create placeholder file
            self._ensure_parent_dir(path)
            with open(path, "wb") as fp:
                fp.write(b"# placeholder written without network\n")
            return

        resp = requests.get(url)  # type: ignore
        try:
            if resp.status_code != 200:
                raise OSError("HTTP error {} for {}".format(resp.status_code, url))
            content = resp.content
            self._ensure_parent_dir(path)
            with open(path, "wb") as fp:
                fp.write(content)
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
