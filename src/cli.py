"""Служебные команды.

uv run python -m src.cli make-admin user@example.com
uv run python -m src.cli make-admin user@example.com --revoke
"""

import argparse
import asyncio

from src.db import async_session_maker_null_pool
from src.utils.db_manager import DBManager


async def set_admin(email: str, is_admin: bool) -> int:
    async with DBManager(session_factory=async_session_maker_null_pool) as db:
        updated = await db.users.set_admin(email, is_admin=is_admin)
        await db.commit()
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.cli", description="Команды HotBook")
    commands = parser.add_subparsers(dest="command", required=True)
    make_admin = commands.add_parser("make-admin", help="Выдать или отозвать права администратора")
    make_admin.add_argument("email")
    make_admin.add_argument("--revoke", action="store_true", help="Отозвать права")
    args = parser.parse_args(argv)

    if args.command == "make-admin":
        if not asyncio.run(set_admin(args.email, is_admin=not args.revoke)):
            print(f"Пользователь {args.email} не найден")
            return 1
        action = "больше не администратор" if args.revoke else "теперь администратор"
        print(f"{args.email} {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
