# scheduler.py
# departmentCrawler.py / repeatCrawler.py / sitemapCrawler.py 스케줄러

import subprocess
import time
import schedule
from pathlib import Path
from datetime import datetime

# === 실행 경로 설정 ======================================================
BASE_DIR = Path(__file__).parent

DEPARTMENT_CRAWLER = BASE_DIR / "departmentCrawler.py"
REPEAT_CRAWLER     = BASE_DIR / "repeatCrawler.py"
SITEMAP_CRAWLER    = BASE_DIR / "sitemapCrawler.py"


# === 실제 실행 함수 ======================================================
def run_department_crawler():
    print("[Scheduler] departmentCrawler 시작")
    subprocess.run(["python", str(DEPARTMENT_CRAWLER)], check=True)
    print("[Scheduler] departmentCrawler 종료")

def run_repeat_crawler():
    print("[Scheduler] repeatCrawler 시작")
    subprocess.run(["python", str(REPEAT_CRAWLER)], check=True)
    print("[Scheduler] repeatCrawler 종료")

def run_sitemap_crawler():
    print("[Scheduler] sitemapCrawler 시작")
    subprocess.run(["python", str(SITEMAP_CRAWLER)], check=True)
    print("[Scheduler] sitemapCrawler 종료")


# === 월 1회(매달 25일)용 래퍼 함수 ======================================
def monthly_department_job():
    today = datetime.now()
    # 매달 25일에만 실행
    if today.day == 25:
        print(f"[Scheduler] 오늘은 {today.strftime('%Y-%m-%d')} (25일) → departmentCrawler 실행")
        run_department_crawler()
    else:
        print(f"[Scheduler] 오늘은 {today.strftime('%Y-%m-%d')} (25일 아님) → departmentCrawler 스킵")


# === 스케줄 설정 =========================================================
# 1) 매달 25일 01:10에 departmentCrawler 실행되도록:
#    → 매일 01:10에 체크해서, 날짜가 25일이면 실행
schedule.every().day.at("01:10").do(monthly_department_job)

# 2) repeatCrawler.py, sitemapCrawler.py는 매일 01:00 실행
schedule.every().day.at("01:00").do(run_repeat_crawler)
schedule.every().day.at("01:00").do(run_sitemap_crawler)


# === 메인 루프 ===========================================================
if __name__ == "__main__":
    print("[Scheduler] 크롤러 스케줄러 시작")

    while True:
        schedule.run_pending()
        time.sleep(1)
