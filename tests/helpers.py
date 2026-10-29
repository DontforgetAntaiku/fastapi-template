import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

BOT_TOKEN = "123456:TEST-TOKEN"


def sign_init_data(
    user: dict, *, auth_date: int | None = None, token: str = BOT_TOKEN
) -> str:
    fields = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "AAH-test",
        "user": json.dumps(user, separators=(",", ":")),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def sign_widget(data: dict, *, token: str = BOT_TOKEN) -> dict:
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    key = hashlib.sha256(token.encode()).digest()
    return {**data, "hash": hmac.new(key, check.encode(), hashlib.sha256).hexdigest()}
