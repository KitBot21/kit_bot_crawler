# test_crawl_demo.py - 시연용 크롤링 데모
import time
import random
from datetime import datetime
from sendToServer import check_and_notify
# test_crawl_demo.py 상단에 추가
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 시연용 가짜 게시글 데이터 (실제 크롤링된 것처럼 보이게)
FAKE_NEW_POSTS = [
    {
        "url": "https://www.kumoh.ac.kr/ko/index.do?sso=ok",
        "title": "[장학] 2025학년도 1학기 국가장학금 신청 안내",
        "board": "공지사항 학사안내"
    },
    {
        "url": "https://www.kumoh.ac.kr/ko/index.do?sso=ok",
        "title": "[학사] 2025학년도 1학기 수강신청 일정 안내",
        "board": "공지사항 학사안내"
    },
    {
        "url": "https://www.kumoh.ac.kr/ko/index.do?sso=ok",
        "title": "[생활관] 2025학년도 1학기 입사 신청 안내",
        "board": "생활관 공지사항"
    },
    {
        "url": "https://www.kumoh.ac.kr/ko/index.do?sso=ok",
        "title": "[행사] 2025 KIT AI 특강 개최 안내",
        "board": "공지사항 행사안내"
    },
    {
        "url": "https://www.kumoh.ac.kr/ko/index.do?sso=ok",
        "title": "[취업] 삼성전자 2025년 상반기 채용설명회 개최",
        "board": "공지사항 학사안내"
    },
    {
        "url": "https://www.kumoh.ac.kr/ko/index.do?sso=ok",
        "title": "[일반] 도서관 운영시간 변경 안내",  # 키워드 없음 - 알림 안 감
        "board": "공지사항 일반소식"
    },
]


def simulate_crawling():
    """크롤링을 시뮬레이션하는 데모"""
    
    print("=" * 70)
    print("🔍 KITBot 크롤러 시작 (시연 모드)")
    print("=" * 70)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"대상: 금오공과대학교 공지사항")
    print("=" * 70)
    
    # 기존에 크롤링된 URL (시뮬레이션)
    existing_urls = set()
    
    stats = {
        "checked": 0,
        "new_found": 0,
        "notifications_sent": 0,
        "no_keyword_match": 0,
    }
    
    print("\n📋 게시판 스캔 중...\n")
    time.sleep(1)
    
    for i, post in enumerate(FAKE_NEW_POSTS, 1):
        stats["checked"] += 1
        
        print(f"[{i}/{len(FAKE_NEW_POSTS)}] 게시글 확인 중...")
        print(f"    게시판: {post['board']}")
        print(f"    제목: {post['title']}")
        print(f"    URL: {post['url'][:50]}...")
        
        time.sleep(0.5)  # 크롤링 딜레이 흉내
        
        # 새 게시글인지 확인 (시뮬레이션)
        if post["url"] not in existing_urls:
            stats["new_found"] += 1
            print(f"    → 🆕 새 게시글 발견!")
            
            # 키워드 매칭 및 알림 전송
            matched, keyword = check_and_notify(post["url"], post["title"])
            
            if matched:
                stats["notifications_sent"] += 1
                print(f"    → 🔔 키워드 [{keyword}] 매칭 - 구독자에게 알림 전송!")
            else:
                stats["no_keyword_match"] += 1
                print(f"    → ⏭️  매칭되는 키워드 없음 - 알림 스킵")
            
            # 크롤링 완료로 표시
            existing_urls.add(post["url"])
        else:
            print(f"    → ⏭️  이미 크롤링된 게시글 - 스킵")
        
        print()
        time.sleep(1.5)  # 다음 게시글까지 딜레이
    
    # 결과 출력
    print("=" * 70)
    print("✅ 크롤링 완료!")
    print("=" * 70)
    print(f"확인한 게시글: {stats['checked']}개")
    print(f"새 게시글: {stats['new_found']}개")
    print(f"알림 전송: {stats['notifications_sent']}건")
    print(f"키워드 미매칭: {stats['no_keyword_match']}건")
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    simulate_crawling()

