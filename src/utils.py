from bs4 import BeautifulSoup
import asyncio
import aiohttp
import os
import openai
import re
import fitz
from fastapi import UploadFile
import random
from question import esg_question


def set_openai_params():
    openai.api_key = os.getenv("OPENAI_API_KEY")
    openai.api_version = os.getenv("OPENAI_API_VERSION")
    openai.api_type = os.getenv("OPENAI_API_TYPE")
    openai.api_base = os.getenv("OPENAI_API_BASE")


async def get_esg_from_bing_news(
    company_name: str, api_key: str, count: int = 30
) -> dict:
    if api_key is None:
        raise Exception("No Bing News API key provided.")
    url = "https://api.bing.microsoft.com/v7.0/news/search"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    mkt = "zh-TW"
    q = f"+{company_name} ESG"
    params = {"q": q, "mkt": mkt, "count": count}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            return await response.json()


async def get_bing_news_dict(json_data) -> dict:
    news_dict = {}
    for item in json_data["value"]:
        title = item.get("name", None)
        url = item.get("url", None)
        if title and url:
            news_dict[title] = url
    return news_dict


async def fetch_page(session, url: str, headers) -> str:
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            return await response.text()
        else:
            print(f"HTTP request failed, status code: {response.status}")
            return None


async def parse_page(html: str) -> dict:
    news_data = {}
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select(".subArticle")

    if not articles:
        print("No relevant news found.")
        return news_data

    for article in articles:
        title_element = article.select_one(".caption h3 a")
        if title_element and title_element["href"]:
            title = title_element.text.strip()
            link = title_element["href"]
            news_data[title] = link

    return news_data


async def get_esg_from_tianxia_news(company_name: str) -> dict:
    base_url = "https://www.cw.com.tw/"
    search_url = f"{base_url}search/doSearch.action?key={company_name}&page="
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    async with aiohttp.ClientSession() as session:
        tasks = []
        for page_num in range(1, 11):
            url = f"{search_url}{page_num}"
            task = asyncio.create_task(fetch_page(session, url, headers))
            tasks.append(task)

        pages_content = await asyncio.gather(*tasks)
        news_data_fromtianxia = {}
        for html in pages_content:
            if html:
                news_data_fromtianxia.update(await parse_page(html))

    return news_data_fromtianxia


async def fetch_both_sources(company_name: str) -> dict:
    bing_news_api_key = os.getenv("Bing_NEWS_API_KEY")
    bing_news = get_esg_from_bing_news(company_name, bing_news_api_key)
    tianxia_news = get_esg_from_tianxia_news(company_name)

    bing_res, tianxia_res_dict = await asyncio.gather(bing_news, tianxia_news)
    bing_res_dict = await get_bing_news_dict(bing_res)
    bing_res_dict.update(tianxia_res_dict)
    return bing_res_dict


async def filter_news_with_ESG(company_name: str, res_list: list) -> dict:
    # response = openai.chat.completions.create(
    #     model="gpt-3.5-turbo-1106",
    #     response_format={"type": "json_object"},
    #     messages=[
    #         {"role": "system", "content": "Assistant is a ESG professional."},
    #         {
    #             "role": "user",
    #             "content": f"Here are some news titles. Please identify which ones are related to ESG (Environmental, Social, and Governance) or Sustainable, and the title must be about {company_name}.",
    #         },
    #         {"role": "assistant", "content": "Please provide the news titles."},
    #         {
    #             "role": "user",
    #             "content": str(res_list),
    #         },
    #         {"role": "assistant", "content": "I will start to identify and analyze."},
    #         {
    #             "role": "user",
    #             "content": f"Give me the json of titles for ESG relevance and must have {company_name}. The returned json's key has been named 'titles'",
    #         },
    #     ],
    # )
    response = openai.ChatCompletion.create(
        engine="gpt35",
        messages=[
            {"role": "system", "content": "Assistant is a ESG professional."},
            {
                "role": "user",
                "content": f"Here are some news titles. Please identify which ones are related to ESG (Environmental, Social, and Governance) or Sustainable, and the title must be about {company_name}.",
            },
            {"role": "assistant", "content": "Please provide the news titles."},
            {
                "role": "user",
                "content": str(res_list),
            },
            {"role": "assistant", "content": "I will start to identify and analyze."},
            {
                "role": "user",
                "content": f"Give me the json of titles for ESG relevance and must have {company_name}. The returned json's key has been named 'titles'",
            },
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content


async def collate_text(content_dict: str, company_name: str) -> str:
    # final_response = openai.chat.completions.create(
    #     model="gpt-4-1106-preview",
    #     messages=[
    #         {
    #             "role": "system",
    #             "content": "Assistant is a sophisticated AI trained to analyze and evaluate ESG-related news.",
    #         },
    #         {
    #             "role": "user",
    #             "content": f"I have several ESG news articles. Please find the content and provide an evaluation for these in terms of their impact on environmental, social, and governance aspects.",
    #         },
    #         {"role": "assistant", "content": "Please provide the news content."},
    #         {
    #             "role": "user",
    #             "content": f"Here are the news articles: {str(content_dict)}. Please pay attention to key environmental, social, and governance factors, consider any notable events or controversies, and record the event's information, like a specific time, occasion, or circumstance.",
    #         },
    #         {"role": "assistant", "content": "I will start to analyze."},
    #         {
    #             "role": "user",
    #             "content": f"Summarize your main findings, the longer the better, give the {company_name}'s pros ,cons, final summary, and you have to give the related article's title to prove it with using '(ref:title)' tag, and must translate all the text except the ref tag presenting into Traditional Chinese for a comprehensive evaluation and you just need to show the words after translated, no words in English.",
    #         },
    #     ],
    # )
    response = openai.ChatCompletion.create(
        engine="gpt4-32k",
        messages=[
            {
                "role": "system",
                "content": "Assistant is a sophisticated AI trained to analyze and evaluate ESG-related news.",
            },
            {
                "role": "user",
                "content": f"I have several ESG news articles. Please find the content and provide an evaluation for these in terms of their impact on environmental, social, and governance aspects.",
            },
            {"role": "assistant", "content": "Please provide the news content."},
            {
                "role": "user",
                "content": f"Here are the news articles: {str(content_dict)}. Please pay attention to key environmental, social, and governance factors, consider any notable events or controversies, and record the event's information, like a specific time, occasion, or circumstance.",
            },
            {"role": "assistant", "content": "I will start to analyze."},
            {
                "role": "user",
                "content": f"Summarize your main findings, the longer the better, give the {company_name}'s pros ,cons, final summary, and you have to give the related article's title to prove it with using '(ref:title)' tag, and must translate all the text except the ref tag presenting into Traditional Chinese for a comprehensive evaluation and you just need to show the words after translated, no words in English.",
            },
        ],
        temperature=0.0,
    )

    return response.choices[0].message.content


async def fetch_url(session, title, url, api_key):
    try:
        async with session.post(
            "https://autoextract.scrapinghub.com/v1/extract",
            auth=aiohttp.BasicAuth(api_key, ""),
            json=[{"url": url, "pageType": "article"}],
        ) as response:
            if response.status == 200:
                article = await response.json()
                return title, article[0]["article"]["articleBody"]
            else:
                return title, None
    except Exception as e:
        print(e)
        return title, None


async def parse_contents(title_dict: dict):
    api_key = os.getenv("ZYTE_API_KEY")
    results = {}
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_url(session, title, url, api_key) for title, url in title_dict.items()
        ]
        responses = await asyncio.gather(*tasks)

        for title, article in responses:
            if article:
                results[title] = article
    return results


def re_content_title_to_url(content: str, title_dict: dict) -> str:
    def replace_with_dict(match):
        key = match.group(1)  # 獲取捕獲組匹配的文本
        replacement = title_dict.get(key, key)
        return f"(ref:{replacement})"

    pattern = r"\(ref:(.+?)\)"
    new_content = re.sub(pattern, replace_with_dict, content)
    return new_content


def ask_company_question(content: str, question: str) -> str:
    # final_response = openai.chat.completions.create(
    #     model=os.getenv("OPENAI_MODEL"),
    #     messages=[
    #         {
    #             "role": "system",
    #             "content": "Assistant is a helper trained to analyze and evaluate ESG-related news.",
    #         },
    #         {
    #             "role": "user",
    #             "content": f"I have several ESG news articles. Please analyze and ready to ask my question.",
    #         },
    #         {"role": "assistant", "content": "Please provide the news content."},
    #         {
    #             "role": "user",
    #             "content": content,
    #         },
    #         {
    #             "role": "assistant",
    #             "content": "I will start to analyze the content and ready to ask your question.",
    #         },
    #         {
    #             "role": "user",
    #             "content": question,
    #         },
    #     ],
    # )
    response = openai.ChatCompletion.create(
        engine="gpt4-32k",
        messages=[
            {
                "role": "system",
                "content": "Assistant is a helper trained to analyze and evaluate ESG-related news.",
            },
            {
                "role": "user",
                "content": f"I have several ESG news articles. Please analyze and ready to ask my question.",
            },
            {"role": "assistant", "content": "Please provide the news content."},
            {
                "role": "user",
                "content": content,
            },
            {
                "role": "assistant",
                "content": "I will start to analyze the content and ready to ask your question.",
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content


def ask_esg_question(content: str) -> str:
    # final_response = openai.chat.completions.create(
    #     model="gpt-4-1106-preview",
    #     messages=[
    #         {
    #             "role": "system",
    #             "content": "Assistant is a helper trained to analyze and evaluate ESG-related question.",
    #         },
    #         {
    #             "role": "user",
    #             "content": f"I have several ESG articles. Please analyze and ask my question.You should use json format to answer each question with the key 'answer' which value only contains 'Yes','No','Unknown',and there is another key named 'Source', you should give me the answer where you find.",
    #         },
    #         {"role": "assistant", "content": "Please provide the articles content."},
    #         {
    #             "role": "user",
    #             "content": content,
    #         },
    #         {
    #             "role": "assistant",
    #             "content": "I will start to analyze the content and ask your question.",
    #         },
    #         {
    #             "role": "user",
    #             "content": str(esg_question),
    #         },
    #     ],
    # )
    response = openai.ChatCompletion.create(
        engine="gpt4-32k",
        messages=[
            {
                "role": "system",
                "content": "Assistant is a helper trained to analyze and evaluate ESG-related question.",
            },
            {
                "role": "user",
                "content": f"I have several ESG articles. Please analyze and ask my question.You should use json format to answer each question with the key 'answer' which value only contains 'Yes','No','Unknown',and there is another key named 'Source', you should give me the answer where you find.",
            },
            {"role": "assistant", "content": "Please provide the articles content."},
            {
                "role": "user",
                "content": content,
            },
            {
                "role": "assistant",
                "content": "I will start to analyze the content and ask your question.",
            },
            {
                "role": "user",
                "content": str(esg_question),
            },
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content


async def extract_text_from_pdf(pdf_file: UploadFile) -> str:
    final_content = ""
    try:
        file_name = os.path.join("temp", pdf_file.filename)
        with open(file_name, "wb") as file:
            content = await pdf_file.read()
            file.write(content)

        with fitz.open(file_name) as doc:
            text = ""
            for page in doc:
                text += page.get_text()
        text = re.sub(r"[^\u4e00-\u9fa5。，]", "", text)
        lines = text.split("。")
        number_of_lines_to_select = 50
        number_of_lines_to_select = min(number_of_lines_to_select, len(lines))
        selected_lines = random.sample(lines, number_of_lines_to_select)
        final_content = "。".join(selected_lines)
    except Exception as e:
        print(e)
    finally:
        os.remove(file_name)
    return final_content
