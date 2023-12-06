from fastapi import FastAPI, Depends
import json
from utils import (
    fetch_both_sources,
    filter_news_with_ESG,
    parse_contents,
    collate_text,
    re_content_title_to_url,
    ask_company_question,
)
from dotenv import load_dotenv
from db import Base, engine, get_db, Company
from sqlalchemy.orm import Session

# 加载 .env 文件
load_dotenv(dotenv_path=".env", verbose=True)

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.get("/company")
async def get_company(company_name: str, db: Session = Depends(get_db)):
    content = await get_content(company_name, db)
    if content:
        return {"content": content}
    news_dict = await fetch_both_sources(company_name)
    news_list = list(news_dict.keys())
    # 從 OpenAI 模型生成的回應中解析出包含新聞標題的 JSON 資料
    title_list_filtered = json.loads(filter_news_with_ESG(company_name, news_list))[
        "titles"
    ]
    title_dict_filtered = {
        k: news_dict[k] for k in title_list_filtered if k in news_dict
    }
    parse_content_dict = await parse_contents(title_dict_filtered)
    content_collated = collate_text(parse_content_dict, company_name)
    final_content = re_content_title_to_url(content_collated, title_dict_filtered)
    await create_company(company_name, parse_content_dict, db)
    return {"content": final_content}


@app.get("/ask/{company_name}")
async def get_company(company_name: str, question: str, db: Session = Depends(get_db)):
    content = await get_content(company_name, db)
    if content is None:
        return {"content": "No content"}
    ask = ask_company_question(content, question)
    return {"content": ask}


async def create_company(company_name: str, content: str, db: Session):
    new_company = Company(company_name=company_name, content=str(content))
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company


@app.get("/companies/{company_name}")
async def get_content(company_name: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.company_name == company_name).first()
    if company is None:
        return None
    return company.content
