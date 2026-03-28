from sqlalchemy.orm import DeclarativeBase


# All database models must inherit from this Base class.
#
# Example:
#   from app.db.base import Base
#
#   class User(Base):
#       __tablename__ = "users"
#       id = mapped_column(Integer, primary_key=True)
#       ...
#
# Two reasons this matters:
#   1. SQLAlchemy uses it to track every table definition so it can run queries.
#   2. Alembic compares models that inherit from Base against the real database
#      to auto-generate migration files (alembic revision --autogenerate).
#
# IMPORTANT: If you create a new model file, import it in alembic/env.py
# (next to the existing Base import) so Alembic can see it during autogenerate.
class Base(DeclarativeBase):
    pass
