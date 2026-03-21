import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, Boolean, Date, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH, override=True)


def resolve_database_url():
    raw_url = (os.getenv("DATABASE_URL") or "").strip()
    raw_password = os.getenv("DATABASE_PASSWORD")

    if not raw_url:
        raise RuntimeError("DATABASE_URL is missing. Set it in backend/.env.")

    placeholders = ["[YOUR-PASSWORD]", "[DATABASE_PASSWORD]", "<PASSWORD>", "{PASSWORD}"]
    if any(token in raw_url for token in placeholders):
        if not raw_password:
            raise RuntimeError(
                "DATABASE_PASSWORD is required when DATABASE_URL contains a password placeholder."
            )

        encoded_password = quote_plus(raw_password)
        for token in placeholders:
            raw_url = raw_url.replace(token, encoded_password)

    return raw_url


DATABASE_URL = resolve_database_url()

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    completed = Column(Boolean, default=False)
    due_date = Column(Date, nullable=True)
    category = Column(String, default="General")
    user_id = Column(Integer, ForeignKey('users.id'))

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

engine = create_engine(DATABASE_URL, echo=True)
Base.metadata.create_all(engine)
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS due_date DATE"))
    conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS category VARCHAR(255) DEFAULT 'General'"))

Session = sessionmaker(bind=engine)