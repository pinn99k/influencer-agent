import os
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SERPER_URL = "https://google.serper.dev/search"


def search(query: str) -> list[dict]:
    """
    Serper API 호출 → 결과 파싱.
    결과 없으면 빈 리스트 반환 — fallback은 경쟁분석 에이전트가 처리.
    반환: [{"title": str, "snippet": str, "link": str}, ...]
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return []

    try:
        resp = requests.post(
            SERPER_URL,
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": 10},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[serper] API error: {type(e).__name__}: {e}")
        return []

    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "link": item.get("link", ""),
        })
    return results
