import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.utils.dataclasses.telegram import TelegramUser
from app.utils.exceptions.telegram import TelegramAuthError


def _check(fields: dict[str, str], key: bytes, max_age: int) -> None:
    received = fields.pop("hash", "")
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    expected = hmac.new(key, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received.encode(), expected.encode()):
        raise TelegramAuthError("bad signature")
    try:
        age = time.time() - int(fields["auth_date"])
    except KeyError, ValueError:
        raise TelegramAuthError("missing auth_date") from None
    if age > max_age or age < -60:
        raise TelegramAuthError("login data expired")


def verify_init_data(init_data: str, bot_token: str, max_age: int) -> TelegramUser:
    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    _check(fields, key, max_age)
    try:
        user = json.loads(fields["user"])
        return TelegramUser(
            id=int(user["id"]),
            first_name=str(user["first_name"]),
            last_name=user.get("last_name"),
            username=user.get("username"),
        )
    except KeyError, ValueError, TypeError:
        raise TelegramAuthError("no user in init data") from None


def verify_widget(
    payload: dict[str, str], bot_token: str, max_age: int
) -> TelegramUser:
    fields = {k: str(v) for k, v in payload.items() if v is not None}
    key = hashlib.sha256(bot_token.encode()).digest()
    _check(fields, key, max_age)
    try:
        return TelegramUser(
            id=int(fields["id"]),
            first_name=fields["first_name"],
            last_name=fields.get("last_name"),
            username=fields.get("username"),
        )
    except KeyError, ValueError:
        raise TelegramAuthError("incomplete widget data") from None
