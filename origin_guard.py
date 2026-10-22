"""Origin-only authentication for the public marketing app behind Front Door.

Render /health remains a minimal GET/HEAD probe. Everything else is protected in
ENFORCE mode. The Front Door rule must OVERWRITE X-CodeJet-Origin-Secret, not
append to or preserve a value supplied by an external client.
"""
from __future__ import annotations

import hmac
import os
from typing import Any, Callable, Iterable, Mapping
from uuid import UUID


class OriginGuard:
    def __init__(self, application: Callable[..., Iterable[bytes]], *, environ: Mapping[str, str] | None = None) -> None:
        self.application = application
        env = os.environ if environ is None else environ
        self.mode = env.get("CODEJET_ORIGIN_GUARD_MODE", "OFF").strip().upper()
        if self.mode not in {"OFF", "ENFORCE"}:
            raise RuntimeError("Unknown origin guard mode.")
        self.secrets: tuple[bytes, ...] = ()
        self.frontdoor_id = b""
        if self.mode == "ENFORCE":
            active = env.get("CODEJET_ORIGIN_SECRET", "")
            previous = env.get("CODEJET_ORIGIN_SECRET_PREVIOUS", "")
            secrets = [value for value in (active, previous) if value]
            if not active or any(len(value) < 43 or len(value) > 256 or not value.isascii() for value in secrets):
                raise RuntimeError("Configure a strong origin secret before enabling enforcement.")
            try:
                self.frontdoor_id = str(UUID(env.get("CODEJET_FRONTDOOR_ID", ""))).encode("ascii")
            except ValueError as exc:
                raise RuntimeError("Configure the Front Door profile ID before enabling enforcement.") from exc
            self.secrets = tuple(value.encode("ascii") for value in secrets)

    def __call__(self, environ: Mapping[str, Any], start_response: Callable[..., Any]) -> Iterable[bytes]:
        if self.mode == "OFF":
            return self.application(environ, start_response)
        if environ.get("PATH_INFO") == "/health" and environ.get("REQUEST_METHOD") in {"GET", "HEAD"}:
            return self.application(environ, start_response)
        supplied = str(environ.get("HTTP_X_CODEJET_ORIGIN_SECRET", "")).encode("utf-8")
        frontdoor = str(environ.get("HTTP_X_AZURE_FDID", "")).lower().encode("utf-8")
        matches = False
        # Evaluate both rotation slots; never log supplied or configured values.
        for secret in self.secrets:
            matches |= hmac.compare_digest(secret, supplied)
        matches &= hmac.compare_digest(self.frontdoor_id, frontdoor)
        if not matches:
            body = b"Forbidden\n"
            start_response("403 Forbidden", [("Content-Type", "text/plain; charset=utf-8"),
                           ("Content-Length", str(len(body))), ("Cache-Control", "no-store")])
            return [] if environ.get("REQUEST_METHOD") == "HEAD" else [body]
        return self.application(environ, start_response)
