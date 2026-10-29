import argparse
import asyncio
import getpass
import os
import sys

from tortoise import Tortoise

from app.core.settings import get_settings
from app.database import build_tortoise_config
from app.database.models import User
from app.utils.auth import hash_password

MIN_PASSWORD_LENGTH = 8


async def create_admin(username: str, password: str) -> User:
    password_hash = await hash_password(password)
    user = await User.get_or_none(username=username)
    if user is None:
        return await User.create(
            username=username,
            first_name=username,
            password_hash=password_hash,
            is_admin=True,
        )
    user.password_hash, user.is_admin, user.is_active = password_hash, True, True
    await user.save()
    return user


async def _run(username: str, password: str) -> None:
    await Tortoise.init(config=build_tortoise_config(get_settings()))
    try:
        user = await create_admin(username, password)
        print(f"admin ready: {user.username} ({user.id})")
    finally:
        await Tortoise.close_connections()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    admin = commands.add_parser("create-admin", help="create or promote an admin")
    admin.add_argument("username")
    args = parser.parse_args()

    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"password must have at least {MIN_PASSWORD_LENGTH} characters")
    asyncio.run(_run(args.username, password))


if __name__ == "__main__":
    main()
