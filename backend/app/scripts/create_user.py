"""创建 / 更新用于登录测试的用户。

用法（在 backend 目录下执行）：
    python -m app.scripts.create_user --username alice --password secret123
    python -m app.scripts.create_user --username alice --password newpass --force
    python -m app.scripts.create_user --username alice --password secret123 --email alice@example.com
    # 也可以直接按文件路径运行：
    python app/scripts/create_user.py --username alice --password secret123

脚本会使用 app/deps.py 里的 DATABASE_URL，并自动创建缺失的表。
"""

import argparse
import sys
from pathlib import Path

# 当前文件位于 backend/app/scripts/，往上三层才是 backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlmodel import Session, select  # noqa: E402

from app.deps import create_db_and_tables, engine  # noqa: E402
from app.models import User  # noqa: E402
from app.services.service_auth import get_password_hash  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="创建或更新 Mood Journal 测试用户")
    parser.add_argument("--username", required=True, help="登录用户名")
    parser.add_argument("--password", required=True, help="明文密码（入库前会哈希）")
    parser.add_argument("--email", default=None, help="可选邮箱")
    parser.add_argument("--full-name", default=None, help="可选全名")
    parser.add_argument(
        "--force",
        action="store_true",
        help="用户已存在时重置密码（默认不覆盖）",
    )
    args = parser.parse_args()

    create_db_and_tables()

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == args.username)
        ).first()

        if user and not args.force:
            print(f"用户 {args.username!r} 已存在；如需重置密码请加 --force")
            return 1

        if user:
            user.hashed_password = get_password_hash(args.password)
            if args.email is not None:
                user.email = args.email
            if args.full_name is not None:
                user.full_name = args.full_name
            action = "已重置密码"
        else:
            user = User(
                username=args.username,
                hashed_password=get_password_hash(args.password),
                email=args.email,
                full_name=args.full_name,
                disabled=False,
            )
            session.add(user)
            action = "已创建"

        session.commit()
        session.refresh(user)

    print(f"用户 {args.username!r} {action}（id={user.id}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
