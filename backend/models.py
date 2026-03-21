import os
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, Boolean, Date, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

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