from fastapi import FastAPI
import json
from .utils import (
    fetch_both_sources,
    filter_news_with_ESG,
    parse_contents,
    collate_text,
)
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(dotenv_path=".env")

app = FastAPI()


@app.get("/company")
async def get_company(company_name: str):
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
    return {"content": content_collated}
