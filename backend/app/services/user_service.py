from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserService:
    @staticmethod
    def get_or_create_user(
        db: Session,
        github_user: dict[str, Any],
    ) -> User:
        github_id = github_user.get("id")
        username = github_user.get("login")
        email = github_user.get("email")

        if not isinstance(github_id, int) or not isinstance(username, str):
            raise ValueError("GitHub user response is missing required fields")

        user = db.scalar(
            select(User).where(User.github_id == github_id)
        )

        if user is None:
            user = User(
                github_id=github_id,
                username=username,
                email=email if isinstance(email, str) else None,
            )
            db.add(user)
        else:
            user.username = username
            user.email = email if isinstance(email, str) else None

        db.commit()
        db.refresh(user)
        return user