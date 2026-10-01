# 쇼츠 벤치마킹 도구

`find_shorts.py` — 키워드로 최근 쇼츠를 검색해 **구독자 대비 조회수 배수**가 높은 영상을 찾습니다. (외부 라이브러리 불필요, Python 3.8+)

## 준비
1. Google Cloud Console에서 **YouTube Data API v3** 활성화 후 API 키 발급
2. `export YOUTUBE_API_KEY=키`

## 사용 예
```bash
python find_shorts.py "주식 상식" --days 30
python find_shorts.py "트로트" --max-subs 50000 --min-views 20000 --top 20
```
결과는 콘솔과 `results.csv`에 출력됩니다.

## 쿼터
검색 1페이지 = 100, videos/channels 조회 = 각 1. 기본(2페이지) 1회 실행 ≈ 205 / 일 10,000.
