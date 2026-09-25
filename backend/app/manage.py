"""Explicit server-side administration: python -m app.manage admin USERNAME."""

import argparse
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.models.user import User


async def set_admin(username: str, revoke: bool) -> None:
    try:
        async with AsyncSessionFactory() as session:
            user = await session.scalar(select(User).where(User.username == username))
            if user is None:
                raise SystemExit(f"User {username!r} does not exist; register the account first.")
            user.is_platform_admin = not revoke
            await session.commit()
            print(f"Platform administrator for {username}: {not revoke}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    admin = commands.add_parser("admin", help="Grant or revoke platform administrator access")
    admin.add_argument("username")
    admin.add_argument("--revoke", action="store_true")
    args = parser.parse_args()
    asyncio.run(set_admin(args.username, args.revoke))
