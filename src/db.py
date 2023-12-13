from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
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
    parsed_content = Column(String)
    pdf_file_name = Column(String)
    pdf_content = Column(String)
    summary = Column(String)
    created_date = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    @classmethod
    def get_all_companies(cls, db: Session):
        return db.query(cls).all()

    @classmethod
    def get_company(cls, company_name: str, db: Session):
        return db.query(cls).filter(cls.company_name == company_name).first()

    @classmethod
    def get_summary(cls, company_name: str, db: Session):
        return db.query(cls).filter(cls.company_name == company_name).first().summary

    @classmethod
    def get_pdf_content(cls, company_name: str, db: Session):
        return (
            db.query(cls).filter(cls.company_name == company_name).first().pdf_content
        )

    @classmethod
    def get_parsed_content(cls, company_name: str, db: Session):
        return (
            db.query(cls)
            .filter(cls.company_name == company_name)
            .first()
            .parsed_content
        )

    @classmethod
    def create_company(
        cls,
        company_name: str,
        parsed_content: dict,
        pdf_file_name: str,
        pdf_content: dict,
        summary: str,
        db: Session,
    ):
        new_company = cls(
            company_name=company_name,
            parsed_content=str(parsed_content),
            pdf_file_name=pdf_file_name,
            pdf_content=str(pdf_content),
            summary=summary,
        )
        db.add(new_company)
        db.commit()
        db.refresh(new_company)
        return new_company

    @classmethod
    def update_pdf(
        cls, company_name, pdf_file_name: str, pdf_content: str, db: Session
    ):
        company = db.query(cls).filter(cls.company_name == company_name).first()
        company.pdf_file_name = pdf_file_name
        company.pdf_content = pdf_content
        db.commit()
        db.refresh(company)
        return company

    @classmethod
    def update_summary(cls, company_name, summary: str, db: Session):
        company = db.query(cls).filter(cls.company_name == company_name).first()
        company.summary = summary
        db.commit()
        db.refresh(company)
        return company
