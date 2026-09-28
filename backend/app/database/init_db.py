from app.database.base import Base
from app.database.connection import engine
from app.models.commit import Commit
from app.models.contributor import Contributor
from app.models.repository import Repository
from app.models.user import User


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)