# server/main.py
from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
from typing import List

app = FastAPI()


class MetaData(BaseModel):
    url: HttpUrl  # 그냥 str 로 하고 싶으면 HttpUrl 대신 str 써도 됩니다.
    keyword: str
    title: str


@app.post("/crawler/keyword")
async def receive_metadata(data: MetaData):
    # TODO: 여기서 DB 저장 / 로그 / 기타 처리 수행
    print(f"받은 URL: {data.url}")
    print(f"키워드: {data.keyword}")
    print(f"제목: {data.title}")
    return {"status": "ok"}
