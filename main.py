from db.database import engine, Base
from db import models  # noqa: F401 — registers models with Base


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("DB connected and tables created.")
