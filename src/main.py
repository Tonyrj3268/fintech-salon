from fastapi import FastAPI, Depends, UploadFile
import json
from utils import (
    fetch_both_sources,
    filter_news_with_ESG,
    parse_contents,
    collate_text,
    re_content_title_to_url,
    ask_company_question,
    extract_text_from_pdf,
)
from dotenv import load_dotenv
from db import Base, engine, get_db, Company
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

# 加载 .env 文件
load_dotenv(dotenv_path="../.env", verbose=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有源
    allow_credentials=True,
    allow_methods=["*"],  # 允許所有方法
    allow_headers=["*"],  # 允許所有標頭
)

Base.metadata.create_all(bind=engine)


@app.post("/company")
async def get_company(
    company_name: str,
    pdf_file: UploadFile = None,
    db: Session = Depends(get_db),
):
    company = Company.get_company(company_name, db)
    if company and pdf_file is None:
        return {"content": company.summary}
    elif company and pdf_file:
        if company.pdf_file_name != pdf_file.filename:
            pdf_text = await extract_text_from_pdf(pdf_file)
            company = Company.update_pdf(company_name, pdf_file.filename, pdf_text, db)
            # TODO update summary
        return {"content": company.summary}
    elif company is None and pdf_file:
        pdf_text = await extract_text_from_pdf(pdf_file)
        pdf_dict = {"Sustainability_Report": pdf_text}

    news_dict = await fetch_both_sources(company_name)
    news_list = list(news_dict.keys())
    # 從 OpenAI 模型生成的回應中解析出包含新聞標題的 JSON 資料
    rs = await filter_news_with_ESG(company_name, news_list)
    title_list_filtered = json.loads(rs)["titles"]
    title_dict_filtered = {
        k: news_dict[k] for k in title_list_filtered if k in news_dict
    }
    parse_content_dict = await parse_contents(title_dict_filtered)
    if pdf_file:
        origin_content = parse_content_dict.copy()
        parse_content_dict.update(pdf_dict)
    content_collated = await collate_text(parse_content_dict, company_name)
    final_content = re_content_title_to_url(content_collated, title_dict_filtered)
    if pdf_file:
        Company.create_company(
            company_name,
            origin_content,
            pdf_file.filename,
            pdf_dict,
            final_content,
            db,
        )
    else:
        Company.create_company(
            company_name, parse_content_dict, None, None, final_content, db
        )
    return {"content": final_content}


@app.get("/ask/{company_name}")
async def get_company(company_name: str, question: str, db: Session = Depends(get_db)):
    parsed_content = await get_parsed_content(company_name, db)
    if parsed_content is None:
        return {"content": "No content"}
    ask = ask_company_question(parsed_content, question)
    return {"content": ask}


@app.get("/all_companies")
async def get_all_companies(db: Session = Depends(get_db)):
    companies = Company.get_all_companies(db)
    return [
        {
            "company_name": company.company_name,
            "created_date": company.created_date,
        }
        for company in companies
    ]


@app.get("/all_companies/{company_name}")
async def get_parsed_content(company_name: str, db: Session = Depends(get_db)):
    return Company.get_parsed_content(company_name, db)
