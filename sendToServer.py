# crawler/send_to_server.py
import requests

# 안드로이드 FastAPI 서버 IP 추가
ANDROID_SERVER = "http://127.0.0.1:8000/crawler/keyword"

# 키워드 리스트 (예: 너가 정한 규칙)
KEYWORDS = ["BOD"]


def send_metadata(url: str, keyword: str, title: str):
    payload = {
        "url": url,
        "keyword": keyword,
        "title": title,
    }

    try:
        resp = requests.post(ANDROID_SERVER, json=payload, timeout=5)
        resp.raise_for_status()
        print(f"[OK] 전송 성공: {url}")
    except Exception as e:
        print(f"[ERR] 전송 실패: {e}")


def process_page(url, title):
    """
    제목(title)에 키워드가 들어 있을 때에만 안드로이드 서버로 전송.
    본문(text_content)은 무시한다.
    """
    for kw in KEYWORDS:
        if kw in title:      # 👍 제목에서만 확인
            send_metadata(url, kw, title)
            break
