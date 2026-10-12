from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=True)
    # MVP only: stores the GitHub token in plaintext so we can call the API
    # on the user's behalf. Encrypt this column before this goes anywhere real.
    access_token = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    github_repo_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    contributors = relationship("Contributor", back_populates="repository")
    commits = relationship("Commit", back_populates="repository")


class Contributor(Base):
    __tablename__ = "contributors"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    github_id = Column(BigInteger, nullable=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=True)

    repository = relationship("Repository", back_populates="contributors")
    commits = relationship("Commit", back_populates="contributor")


class Commit(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    contributor_id = Column(Integer, ForeignKey("contributors.id"), nullable=False)
    commit_sha = Column(String, unique=True, nullable=False, index=True)
    message = Column(Text, nullable=True)
    commit_date = Column(DateTime, nullable=False)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    files_changed = Column(Integer, default=0)

    repository = relationship("Repository", back_populates="commits")
    contributor = relationship("Contributor", back_populates="commits")
