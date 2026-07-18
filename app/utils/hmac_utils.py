import hashlib
import hmac
import json
from typing import Any


def generate_webhook_signature(secret_key: str, payload: Any) -> tuple[bytes, str]:
    """
    Generate JSON payload and HMAC SHA256 signature.
    """
    payload_bytes = json.dumps(payload).encode("utf-8")

    signature = hmac.new(
        key=secret_key.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256
    ).hexdigest()

    return payload_bytes, signature
