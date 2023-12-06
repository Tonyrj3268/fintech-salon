from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

DATABASE_URL = "sqlite:///./test.db"
Base = declarative_base()

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Company(Base):
    __tablename__ = "companies"
    index = Column(Integer, primary_key=True)
    company_name = Column(String)
    content = Column(String)
    created_date = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
