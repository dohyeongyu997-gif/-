#!/usr/bin/env python3
"""YouTube 쇼츠 벤치마킹 후보 탐색기.

키워드로 최근 쇼츠를 검색하고 '구독자 대비 조회수 배수'가 높은 영상을 골라준다.

사용법:
    export YOUTUBE_API_KEY=발급받은키
    python find_shorts.py "주식 상식" --days 30 --region KR --lang ko
"""
import argparse
import csv
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://www.googleapis.com/youtube/v3"


def call(endpoint, key, **params):
    params["key"] = key
    url = f"{API}/{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"API 오류 {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")


def parse_duration(iso):
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    h, mi, s = (int(x or 0) for x in m.groups()) if m else (0, 0, 0)
    return h * 3600 + mi * 60 + s


def chunks(seq, n=50):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def search_ids(key, query, days, region, lang, pages):
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids, token = [], None
    for _ in range(pages):
        p = dict(part="id", q=f"{query} #shorts", type="video", videoDuration="short",
                 order="viewCount", publishedAfter=after, maxResults=50)
        if region:
            p["regionCode"] = region
        if lang:
            p["relevanceLanguage"] = lang
        if token:
            p["pageToken"] = token
        data = call("search", key, **p)
        ids += [i["id"]["videoId"] for i in data.get("items", [])]
        token = data.get("nextPageToken")
        if not token:
            break
    return ids


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", help="검색 키워드")
    ap.add_argument("--days", type=int, default=30, help="최근 N일 (기본 30)")
    ap.add_argument("--region", default="KR", help="국가 코드 (기본 KR)")
    ap.add_argument("--lang", default="ko", help="언어 코드 (기본 ko)")
    ap.add_argument("--pages", type=int, default=2, help="검색 페이지 수, 페이지당 쿼터 100 (기본 2)")
    ap.add_argument("--max-seconds", type=int, default=60, help="쇼츠 최대 길이(초) (기본 60)")
    ap.add_argument("--min-views", type=int, default=10000, help="최소 조회수 (기본 10000)")
    ap.add_argument("--max-subs", type=int, default=0, help="채널 최대 구독자 수 (0=제한 없음)")
    ap.add_argument("--top", type=int, default=30, help="출력 개수 (기본 30)")
    ap.add_argument("--out", default="results.csv", help="CSV 저장 경로")
    a = ap.parse_args()

    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        sys.exit("YOUTUBE_API_KEY 환경변수를 설정하세요.")

    ids = search_ids(key, a.query, a.days, a.region, a.lang, a.pages)
    if not ids:
        sys.exit("검색 결과가 없습니다.")

    videos = []
    for part in chunks(ids):
        data = call("videos", key, part="snippet,statistics,contentDetails", id=",".join(part))
        videos += data.get("items", [])

    channel_ids = sorted({v["snippet"]["channelId"] for v in videos})
    subs = {}
    for part in chunks(channel_ids):
        data = call("channels", key, part="statistics", id=",".join(part))
        for c in data.get("items", []):
            st = c["statistics"]
            subs[c["id"]] = None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0))

    rows = []
    for v in videos:
        dur = parse_duration(v["contentDetails"]["duration"])
        st = v["statistics"]
        views = int(st.get("viewCount", 0))
        if dur == 0 or dur > a.max_seconds or views < a.min_views:
            continue
        cid = v["snippet"]["channelId"]
        sub = subs.get(cid)
        if a.max_subs and (sub is None or sub > a.max_subs):
            continue
        likes = int(st.get("likeCount", 0))
        rows.append({
            "ratio": round(views / sub, 2) if sub else 0,
            "views": views,
            "subs": sub if sub is not None else "",
            "like_rate_%": round(likes / views * 100, 2) if views else 0,
            "comments": int(st.get("commentCount", 0)),
            "seconds": dur,
            "published": v["snippet"]["publishedAt"][:10],
            "channel": v["snippet"]["channelTitle"],
            "title": v["snippet"]["title"],
            "url": f"https://www.youtube.com/shorts/{v['id']}",
        })

    rows.sort(key=lambda r: (r["ratio"], r["views"]), reverse=True)
    rows = rows[:a.top]
    if not rows:
        sys.exit("조건에 맞는 영상이 없습니다. --min-views 를 낮추거나 --days 를 늘려보세요.")

    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    for i, r in enumerate(rows, 1):
        print(f"{i:>2}. 배수 {r['ratio']:>7}x | 조회 {r['views']:>10,} | 구독 {r['subs']!s:>9} | "
              f"{r['seconds']}s | {r['channel']}\n    {r['title']}\n    {r['url']}")
    print(f"\n{len(rows)}개 저장 → {a.out}")


if __name__ == "__main__":
    main()
