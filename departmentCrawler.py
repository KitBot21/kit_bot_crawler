#!/usr/bin/env python3
"""
departmentCrawler.py

학과 소개 / 동아리 소개 / 교육과정(정적 페이지 위주) 1회성 크롤러
- 자주 변하지 않는 정적 정보용
- 기존 SimpleTestCrawler 로직을 복붙/경량화한 버전
"""

import sys
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging
import hashlib
import urllib.parse

# 환경 변수 로드
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# crawler 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from filters.content_extractor import ContentExtractor
from filters.quality_filter import QualityFilter
from storage.json_storage import JSONStorage
from storage.minio_storage import MinIOStorage
from sendToServer import process_page

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

exclude_patterns = [
    "/cms/fileDownload.do",
]
# 페이지 크롬(로고, 메뉴, SNS, 버튼 등) 이미지 필터
ICON_IMAGE_KEYWORDS = [
    "/_res/ko/img/icon/",
    "/_res/ko/img/common/",
    "logo",
    "btn_",
    "btn-",
    "bg_subvisual",
    "wa-mark",
    "bubble_tail",
    "btn_top_go",
]

class departmentCrawler:
    """학과/동아리/정적 소개 페이지 전용 크롤러"""

    def __init__(self, enable_minio: bool = False):
        """
        Args:
            enable_minio: MinIO 사용 여부 (True면 첨부파일을 MinIO에 업로드)
        """
        # MinIO 설정
        self.enable_minio = enable_minio
        if enable_minio:
            try:
                self.minio = MinIOStorage.from_env()
                logger.info("✅ MinIO 스토리지 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️  MinIO 초기화 실패: {e}")
                logger.warning("   첨부파일은 메타데이터만 기록됩니다.")
                self.enable_minio = False
                self.minio = None
        else:
            self.minio = None

        # ✅ 여기 리스트에 학과/동아리/교육과정 정적 페이지들을 계속 추가
        self.department_static_urls = [
            # 에디슨칼리지 첨단산업융합학부
            {
                "url": "https://edison.kumoh.ac.kr/edison/sub0101.do",
                "name": "에디슨칼리지 첨단산업융합학부 소개",
            },
            {
                "url": "https://edison.kumoh.ac.kr/edison/sub0102.do",
                "name": "에디슨칼리지 첨단산업융합학부 교육목표",
            },
            {
                "url": "https://edison.kumoh.ac.kr/edison/sub0104.do",
                "name": "에디슨칼리지 첨단산업융합학부 비전",
            },

            # 건축토목환경공학부
            {
                "url": "https://archi.kumoh.ac.kr/archi/sub0102.do",
                "name": "건축토목환경공학부 소개",
            },
            {
                "url": "https://archi.kumoh.ac.kr/archi/sub0103.do",
                "name": "건축토목환경공학부 건축학전공 소개",
            },
            {
                "url": "https://archi.kumoh.ac.kr/archi/sub0104.do",
                "name": "건축토목환경공학부 건축공학전공 소개",
            },
            {
                "url": "https://civil.kumoh.ac.kr/civil/sub0101.do",
                "name": "건축토목환경공학부 토목공학전공 소개",
            },
            {
                "url": "https://env.kumoh.ac.kr/env/sub0101.do",
                "name": "건축토목환경공학부 환경공학전공 소개",
            },
            {
                "url": "https://env.kumoh.ac.kr/env/sub0202_01.do",
                "name": "건축토목환경공학부 환경공학전공 동아리 지구환경연구회 소개",
            },
            {
                "url": "https://env.kumoh.ac.kr/env/sub0202_02.do",
                "name": "건축토목환경공학부 환경공학전공 동아리 아름드리 소개",
            },
            {
                "url": "https://env.kumoh.ac.kr/env/sub0202_03.do",
                "name": "건축토목환경공학부 환경공학전공 동아리 ESC 소개",
            },
            {
                "url": "https://env.kumoh.ac.kr/env/sub0202_04.do",
                "name": "건축토목환경공학부 환경공학전공 동아리 BOD 소개",
            },

            # 기계공학부
            {
                "url": "https://mecheng.kumoh.ac.kr/mecheng/sub0101.do",
                "name": "기계공학부 기계공학전공 소개",
            },
            {
                "url": "https://mx.kumoh.ac.kr/md/sub0101.do",
                "name": "기계공학부 기계시스템공학전공 소개",
            },
            {
                "url": "https://mobility.kumoh.ac.kr/smartmobility/sub0101.do",
                "name": "기계공학부 스마트모빌리티전공 인사말",
            },
            {
                "url": "https://mobility.kumoh.ac.kr/smartmobility/sub0102.do",
                "name": "기계공학부 스마트모빌리티전공 교육 목표",
            },
            {
                "url": "https://mobility.kumoh.ac.kr/smartmobility/sub0301.do",
                "name": "기계공학부 스마트모빌리티전공 공동학과 교육 과정",
            },
            {
                "url": "https://mobility.kumoh.ac.kr/smartmobility/sub0304.do",
                "name": "기계공학부 스마트모빌리티전공 이수체계도",
            },

            # 산업빅데이터공학부
            {
                "url": "https://ie.kumoh.ac.kr/ie/sub0102.do",
                "name": "산업빅데이터공학부 산업공학전공 소개",
            },
            {
                "url": "https://ie.kumoh.ac.kr/ie/sub0603.do",
                "name": "산업빅데이터공학부 산업공학전공 동아리/학생회",
            },
            {
                "url": "https://www.kumoh.ac.kr/bigdata/sub0102.do",
                "name": "산업빅데이터공학부 수리빅데이터전공 개요 및 연혁",
            },
            {
                "url": "https://www.kumoh.ac.kr/bigdata/sub0502.do",
                "name": "산업빅데이터공학부 수리빅데이터전공 전공동아리",
            },

            # 재료공학부
            {
                "url": "https://polymer.kumoh.ac.kr/polymer/sub0202.do",
                "name": "재료공학부 고분자공학전공 전공소개",
            },
            {
                "url": "https://polymer.kumoh.ac.kr/polymer/sub0502.do",
                "name": "재료공학부 고분자공학전공 동아리",
            },
            {
                "url": "https://mse.kumoh.ac.kr/mse/sub0102.do",
                "name": "재료공학부 신소재공학전공 전공소개",
            },
            {
                "url": "https://mse.kumoh.ac.kr/mse/sub020102.do",
                "name": "재료공학부 신소재공학전공 교육과정 편성표",
            },
            {
                "url": "https://mse.kumoh.ac.kr/mse/sub0602.do",
                "name": "재료공학부 신소재공학전공 동아리",
            },

            # 전자공학부
            {
                "url": "https://see.kumoh.ac.kr/see/sub0101.do",
                "name": "전자공학부 반도체시스템전공 전자시스템전공 소개",
            },
            {
                "url": "https://see.kumoh.ac.kr/see/sub0501.do",
                "name": "전자공학부 반도체시스템전공 전자시스템전공 동아리",
            },

            # 컴퓨터공학부 - 소프트웨어전공
            {
                "url": "https://cs.kumoh.ac.kr/cs/sub0101.do",
                "name": "컴퓨터공학부 소프트웨어전공 소개",
            },
            {
                "url": "https://cs.kumoh.ac.kr/cs/sub0105_2.do",
                "name": "컴퓨터공학부 소프트웨어전공 교육과정",
            },
            {
                "url": "https://cs.kumoh.ac.kr/cs/sub0504.do",
                "name": "컴퓨터공학부 소프트웨어전공 동아리",
            },

            # 컴퓨터공학부 - 인공지능공학전공
            {
                "url": "https://ai.kumoh.ac.kr/ai/sub0102.do",
                "name": "컴퓨터공학부 인공지능공학전공 개요 및 연혁",
            },
            {
                "url": "https://ai.kumoh.ac.kr/ai/sub0302.do",
                "name": "컴퓨터공학부 인공지능공학전공 교육과정표",
            },
            {
                "url": "https://ai.kumoh.ac.kr/ai/sub0602.do",
                "name": "컴퓨터공학부 인공지능공학전공 전공동아리",
            },

            # 컴퓨터공학부 - 컴퓨터공학전공
            {
                "url": "https://ce.kumoh.ac.kr/ce/sub0102.do",
                "name": "컴퓨터공학부 컴퓨터공학전공 개요 및 연혁",
            },
            {
                "url": "https://ce.kumoh.ac.kr/ce/sub0205.do",
                "name": "컴퓨터공학부 컴퓨터공학전공 동아리",
            },
            {
                "url": "https://ce.kumoh.ac.kr/ce/sub0301.do",
                "name": "컴퓨터공학부 컴퓨터공학전공 교과과정",
            },

            # 화학소재공학부 - 소재디자인공학전공
            {
                "url": "https://textile.kumoh.ac.kr/textile/sub0101.do",
                "name": "화학소재공학부 소재디자인공학전공 전공장 인사말",
            },
            {
                "url": "https://textile.kumoh.ac.kr/textile/sub0203.do",
                "name": "화학소재공학부 소재디자인공학전공 교육과정",
            },
            {
                "url": "https://textile.kumoh.ac.kr/textile/sub0501.do",
                "name": "화학소재공학부 소재디자인공학전공 전공동아리",
            },

            # 화학소재공학부 - 화학공학전공
            {
                "url": "https://che.kumoh.ac.kr/che/sub0102.do",
                "name": "화학소재공학부 화학공학전공 학과소개",
            },
            {
                "url": "https://che.kumoh.ac.kr/che/sub0502.do",
                "name": "화학소재공학부 화학공학전공 동아리",
            },

            # 화학소재공학부 - 화학생명소재전공
            {
                "url": "https://chembio.kumoh.ac.kr/chembio/sub0102.do",
                "name": "화학소재공학부 화학생명소재전공 전공개요",
            },

            # 광시스템공학과
            {
                "url": "https://optics.kumoh.ac.kr/optics/sub0101.do",
                "name": "광시스템공학과 학과소개",
            },

            # 바이오메디컬공학과
            {
                "url": "https://medicalit.kumoh.ac.kr/medicalit/sub0101.do",
                "name": "바이오메디컬공학과 학과소개",
            },
            {
                "url": "https://medicalit.kumoh.ac.kr/medicalit/sub020102.do",
                "name": "바이오메디컬공학과 교과소개",
            },

            # IT융합학과
            {
                "url": "https://itc.kumoh.ac.kr/itc/sub0101.do",
                "name": "IT융합학과 학과소개",
            },
            {
                "url": "https://itc.kumoh.ac.kr/itc/sub0103.do#accordion-menu-title",
                "name": "IT융합학과 교과목개요",
            },

            # 자율전공학부
            {
                "url": "https://sls.kumoh.ac.kr/sls/sub0101.do",
                "name": "자율전공학부 소개",
            },
            {
                "url": "https://sls.kumoh.ac.kr/sls/sub0301.do",
                "name": "자율전공학부 교과과정",
            },
            {
                "url": "https://sls.kumoh.ac.kr/sls/sub0302.do",
                "name": "자율전공학부 전공선택",
            },

            # 경영학과
            {
                "url": "https://biz.kumoh.ac.kr/biz/sub0102.do",
                "name": "경영학과 소개",
            },
            {
                "url": "https://biz.kumoh.ac.kr/biz/sub0702.do",
                "name": "경영학과 동아리",
            },
        ]

        self.department_board_urls = [
            {
                "url": "https://archi.kumoh.ac.kr/archi/sub0201.do",
                "name": "건축토목환경공학부 건축학전공 교육과정"
            },
            {
                "url": "https://archi.kumoh.ac.kr/archi/sub0202.do",
                "name": "건축토목환경공학부 건축공학전공 교육과정"
            },
            {
                "url": "https://civil.kumoh.ac.kr/civil/sub030101.do",
                "name": "건축토목환경공학부 토목공학전공 교육과정"
            },
            {
                "url": "https://ie.kumoh.ac.kr/ie/sub030101.do",
                "name": "산업빅데이터공학부 산업공학전공 교육과정"
            },
            {
                "url": "https://www.kumoh.ac.kr/bigdata/sub030102.do",
                "name": "산업빅데이터공학부 수리빅데이터전공 교육과정표"
            },
            {
                "url": "https://polymer.kumoh.ac.kr/polymer/sub0404.do",
                "name": "재료공학부 고분자공학전공 교과과정"
            },
            {
                "url": "https://che.kumoh.ac.kr/che/sub0304.do",
                "name": "화학소재공학부 화학공학전공 교과과정"
            },
            {
                "url": "https://chembio.kumoh.ac.kr/chembio/sub030101.do",
                "name": "화학소재공학부 화학생명소재전공 교육과정 및 교과목 개요",
            },
            {
                "url": "https://optics.kumoh.ac.kr/optics/sub020102.do",
                "name": "광시스템공학과 학부교육과정"
            },
            {
                "url": "https://biz.kumoh.ac.kr/biz/sub030101.do",
                "name": "경영학과 교과과정"
            },
        ]

        # 필터 및 저장소 초기화
        self.quality_filter = QualityFilter(
            min_text_length=50,      # 소개 페이지는 너무 빡세지 않게 조금만 완화
            max_text_length=500000,
            min_word_count=10
        )

        output_dir = Path(__file__).parent.parent / "data" / "first_crawled"
        self.storage = JSONStorage(output_dir, pretty_print=True)

        self.content_extractor = ContentExtractor(
            keep_links=True,
            keep_images=False
        )

        # 통계
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "filtered": 0,
            "skipped": 0,
            "attachments_found": 0,
            "attachments_uploaded": 0,
        }

        self.saved_pages = []
        self.existing_urls = set()
        self._load_existing_index()

    def _load_existing_index(self):
        """기존 인덱스 파일을 읽어서 이미 크롤링한 URL 목록을 가져옵니다."""
        output_dir = Path(__file__).parent.parent / "data" / "first_crawled"
        index_file = output_dir / "crawl_index.json"

        if index_file.exists():
            try:
                import json
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for page in data.get('pages', []):
                        url = page.get('url')
                        if url:
                            self.existing_urls.add(url)
                            self.saved_pages.append(page)
                logger.info(f"📂 기존 first 크롤링 데이터 로드: {len(self.existing_urls)}개 URL")
            except Exception as e:
                logger.warning(f"기존 인덱스 로드 실패: {e}")

    def crawl_url(self, url: str, page_info: dict) -> bool:
        """
        단일 정적 페이지 크롤링 (학과소개, 동아리소개, 교육과정 등)
        - 날짜 필터 없음
        """
        self.stats["total"] += 1

        if url in self.existing_urls:
            logger.info(f"⏭️  이미 크롤링된 URL - 건너뜀: {url}")
            self.stats["skipped"] += 1
            return False

        logger.info(f"크롤링 시작: {url}")

        try:
            headers = {
                'User-Agent': 'KITBot/2.0 (CSEcapstone, contact: cdh5113@naver.com)'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            html = response.text

            # 품질 검사
            is_quality, reason = self.quality_filter.is_high_quality(html, url)
            if not is_quality:
                logger.warning(f"품질 필터 실패: {reason}")
                self.stats["filtered"] += 1
                return False

            # 본문 추출
            content_data = self.content_extractor.extract_with_metadata(html)

            # 첨부파일 추출 및 처리
            attachments = self._process_attachments(url, html)

            # ✅ 1) page_type을 제일 먼저 결정
            page_type = page_info.get("page_type", "static_intro")

            # ✅ 2) board_name / title / display_title 정리
            if page_type == "static_intro":
                # 정적 소개/비전/교육과정 페이지:
                # - board_name: 사이트 전체 경로(HTML <title>)
                # - title/display_title: 사람이 보기 좋은 이름(page_info["name"])
                board_name = content_data["title"] or page_info["name"]
                title = page_info["name"]
                display_title = title
            else:
                # 게시판 최신글 같은 케이스(board_notice 등)
                # - board_name: 상위 게시판 이름
                # - title: 게시글 제목(일단 HTML <title> 사용)
                board_name = page_info.get("board_name") or page_info["name"]
                title = content_data["title"] or page_info["name"]
                display_title = title          

            # 게시판 상세 페이지면 작성자/조회수/작성일 추출
            author = None
            view_count = None
            created_at = None

            if "board_notice" in page_type or "latest" in page_info["name"]:
                try:
                    soup = BeautifulSoup(html, "html.parser")

                    # 작성자
                    el_author = soup.find(text="작성자")
                    if el_author and el_author.parent:
                        author = el_author.parent.find_next().get_text(strip=True)

                    # 조회수
                    el_view = soup.find(text="조회")
                    if el_view and el_view.parent:
                        view_count = el_view.parent.find_next().get_text(strip=True)
                        view_count = int(view_count) if view_count.isdigit() else None

                    # 작성일
                    el_date = soup.find(text="작성일")
                    if el_date and el_date.parent:
                        created_raw = el_date.parent.find_next().get_text(strip=True)
                        # ISO 형식으로 변환
                        created_at = created_raw.replace('.', '-').strip()
                        try:
                            created_at = datetime.strptime(created_at, "%Y-%m-%d").isoformat()
                        except:
                            created_at = None

                except Exception as e:
                    print("[WARN] 게시판 메타 파싱 실패:", e)

            # 메타데이터 준비
            metadata = {
                "text_length": len(content_data['text']),
                "word_count": content_data['word_count'],
                "title": title,
                "board_name": board_name,
                "display_title": display_title,
                "paragraphs": content_data['paragraphs'],
                "link_count": len(content_data['links']),
                "attachments_count": len(attachments),
                "attachments": attachments,
                "images": content_data['images'],
                "quality_check": reason,
                "crawled_at": datetime.now().isoformat(),
                "source_url": url,
                "page_type": page_type,   # 학과/동아리/소개 페이지 태그
                "name": page_info["name"],
                "author": author,
                "view_count": view_count,
                "created_at": created_at,
            }

            # 저장
            filepath = self.storage.save_page(url, html, metadata)

            self.saved_pages.append({
                "url": url,
                "file": filepath,
                "title": content_data['title'],
                "text_length": len(content_data['text']),
                "page_type": metadata["page_type"],
            })

            self.existing_urls.add(url)
            self.stats["success"] += 1

            logger.info(f"✅ 저장 완료: {Path(filepath).name}")
            logger.info(f"   제목: {content_data['title'][:80]}...")
            logger.info(f"   본문 길이: {len(content_data['text'])} 문자")
            logger.info(f"   문단 수: {content_data['paragraphs']}")

            # ✅ 안드로이드 서버로 메타데이터 전송 (키워드 필터 적용)
            try:
                process_page(
                    url=url,
                    title=metadata["title"],
                )
            except Exception as e:
                logger.warning(f"⚠️ 안드로이드 메타데이터 전송 중 오류: {e}")
            return True

        except requests.RequestException as e:
            logger.error(f"❌ 네트워크 에러: {e}")
            self.stats["failed"] += 1
            return False

        except Exception as e:
            logger.error(f"❌ 처리 에러: {e}")
            self.stats["failed"] += 1
            return False

    def _process_attachments(self, page_url: str, html: str) -> list:
        """
        HTML에서 첨부파일 링크를 추출하고 MinIO에 업로드

        - mode=download, .pdf, .hwp, .docx, .xlsx, .pptx, .zip 등
        - 학과/동아리 소개 페이지에도 교육과정 pdf 등이 있을 수 있으므로 재사용
        """
        attachments = []

        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text(strip=True)

                is_download = (
                    'mode=download' in href or
                    'download' in href.lower() or
                    any(href.lower().endswith(ext) for ext in [
                        '.pdf', '.hwp', '.docx', '.xlsx', '.pptx', '.zip'
                    ])
                )

                if any(pattern in href for pattern in exclude_patterns):
                    is_download = False

                if not is_download:
                    continue

                # 절대 URL로 변환 (도메인 상관없이 안전하게)
                abs_url = urllib.parse.urljoin(page_url, href)

                self.stats["attachments_found"] += 1

                attachment_info = {
                    "page_url": page_url,
                    "link_text": link_text,
                    "download_url": abs_url,
                    "detected_at": datetime.now().isoformat(),
                }

                if self.enable_minio and self.minio:
                    try:
                        headers = {
                            'User-Agent': 'KITBot/2.0 (CSEcapstone, contact: cdh5113@naver.com)',
                            'Referer': page_url,
                        }
                        resp = requests.get(abs_url, headers=headers, timeout=30)
                        resp.raise_for_status()

                        file_data = resp.content
                        content_type = resp.headers.get('Content-Type', 'application/octet-stream')

                        # 파일명 추출
                        content_disp = resp.headers.get('Content-Disposition', '')
                        if 'filename=' in content_disp:
                            filename = content_disp.split('filename=')[-1].strip('"\'')
                        else:
                            filename = abs_url.split('/')[-1].split('?')[0]
                            if not filename or '.' not in filename:
                                if link_text and '.' in link_text:
                                    filename = link_text
                                else:
                                    filename = f"attachment_{hashlib.md5(abs_url.encode()).hexdigest()[:8]}.bin"

                        # URL 디코딩
                        try:
                            filename = urllib.parse.unquote(filename)
                        except Exception:
                            pass

                        # 경로 구분자 제거
                        clean_filename = filename.replace('/', '_').replace('\\', '_')
                        file_hash = hashlib.sha256(file_data).hexdigest()[:16]

                        object_name = f"attachments/{clean_filename}"
                        if self.minio.file_exists(object_name):
                            if '.' in clean_filename:
                                name_part, ext = clean_filename.rsplit('.', 1)
                                object_name = f"attachments/{name_part}_{file_hash[:8]}.{ext}"
                            else:
                                object_name = f"attachments/{clean_filename}_{file_hash[:8]}"

                        success, result = self.minio.upload_file(
                            file_data=file_data,
                            object_name=object_name,
                            content_type=content_type,
                            original_filename=filename,
                            metadata={
                                "source_url": abs_url,
                                "page_url": page_url,
                                "link_text": link_text,
                            }
                        )

                        if success:
                            attachment_info["minio_url"] = result
                            attachment_info["minio_object"] = object_name
                            attachment_info["file_size"] = len(file_data)
                            attachment_info["sha256"] = file_hash
                            attachment_info["filename"] = clean_filename
                            attachment_info["status"] = "uploaded"
                            self.stats["attachments_uploaded"] += 1
                            logger.info(f"   📎 첨부파일 업로드: {clean_filename} ({len(file_data):,} bytes)")
                        else:
                            attachment_info["status"] = "upload_failed"
                            attachment_info["error"] = result
                            logger.warning(f"   ⚠️  첨부파일 업로드 실패: {filename}")
                    except Exception as e:
                        attachment_info["status"] = "download_failed"
                        attachment_info["error"] = str(e)
                        logger.warning(f"   ⚠️  첨부파일 다운로드 실패: {link_text} - {e}")
                else:
                    attachment_info["status"] = "metadata_only"

                attachments.append(attachment_info)

            # 2) 이미지(img src) 첨부 처리
            image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']

            for img in soup.find_all('img', src=True):
                src = img['src']
                alt_text = img.get('alt', '').strip()

                # 0) 사이트 공통 아이콘/로고/버튼/배경 이미지는 스킵
                if any(key in src for key in ICON_IMAGE_KEYWORDS):
                    continue

                # 1) 확장자/패턴 체크
                src_no_query = src.split('?', 1)[0].lower()
                is_image_by_ext = any(src_no_query.endswith(ext) for ext in image_exts)
                is_editor_image = 'editorimage.do' in src_no_query  # 본문 이미지

                if not (is_image_by_ext or is_editor_image):
                    continue

                # 절대 URL 변환
                abs_url = urllib.parse.urljoin(page_url, src)

                self.stats["attachments_found"] += 1

                attachment_info = {
                    "page_url": page_url,
                    "link_text": alt_text or "(image)",
                    "download_url": abs_url,
                    "detected_at": datetime.now().isoformat(),
                    "type": "image",   # ← 이미지 타입 표시
                }

                if self.enable_minio and self.minio:
                    try:
                        headers = {
                            'User-Agent': 'KITBot/2.0 (CSEcapstone, contact: cdh5113@naver.com)'
                        }
                        resp = requests.get(abs_url, headers=headers, timeout=30)
                        resp.raise_for_status()

                        file_data = resp.content
                        content_type = resp.headers.get('Content-Type', 'image/*')

                        # 파일명 추출 (URL 기준)
                        filename = abs_url.split('/')[-1].split('?')[0]
                        if not filename:
                            filename = f"image_{hashlib.md5(abs_url.encode()).hexdigest()[:8]}.bin"

                        # URL 디코딩
                        try:
                            filename = urllib.parse.unquote(filename)
                        except Exception:
                            pass

                        clean_filename = filename.replace('/', '_').replace('\\', '_')
                        file_hash = hashlib.sha256(file_data).hexdigest()[:16]

                        object_name = f"images/{clean_filename}"
                        # 이미 같은 object_name이 있으면 해시 일부를 붙여서 충돌 방지
                        if self.minio.file_exists(object_name):
                            if '.' in clean_filename:
                                name_part, ext = clean_filename.rsplit('.', 1)
                                object_name = f"images/{name_part}_{file_hash[:8]}.{ext}"
                            else:
                                object_name = f"images/{clean_filename}_{file_hash[:8]}"

                        success, result = self.minio.upload_file(
                            file_data=file_data,
                            object_name=object_name,
                            content_type=content_type,
                            original_filename=filename,
                            metadata={
                                "source_url": abs_url,
                                "page_url": page_url,
                                "alt_text": alt_text,
                            }
                        )

                        if success:
                            attachment_info["minio_url"] = result
                            attachment_info["minio_object"] = object_name
                            attachment_info["file_size"] = len(file_data)
                            attachment_info["sha256"] = file_hash
                            attachment_info["filename"] = clean_filename
                            attachment_info["status"] = "uploaded"
                            self.stats["attachments_uploaded"] += 1
                            logger.info(f"   🖼 이미지 업로드: {clean_filename} ({len(file_data):,} bytes)")
                        else:
                            attachment_info["status"] = "upload_failed"
                            attachment_info["error"] = result
                            logger.warning(f"   ⚠️  이미지 업로드 실패: {filename}")
                    except Exception as e:
                        attachment_info["status"] = "download_failed"
                        attachment_info["error"] = str(e)
                        logger.warning(f"   ⚠️  이미지 다운로드 실패: {alt_text or src} - {e}")
                else:
                    attachment_info["status"] = "metadata_only"

                attachments.append(attachment_info)

        except Exception as e:
            logger.error(f"❌ 첨부파일 처리 에러: {e}")

        return attachments

    def crawl_latest_from_department_board(self, board_info):
        """
        교육과정 게시판에서 '최신 게시글 1개만' 크롤링하는 함수
        """
        url = board_info["url"]
        name = board_info["name"]

        logger.info(f"\n📘 [교육과정] {name}: {url}")

        try:
            headers = {
                'User-Agent': 'KITBot/2.0 (CSEcapstone)'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 게시글 링크 찾기 (기존 crawl_list_page와 동일한 방식)
            article_links = []

            for link in soup.find_all('a', href=True):
                href = link['href']
                if ('mode=view' in href) or ('articleNo' in href):
                    # 절대 경로 변환
                    if href.startswith('/'):
                        site_root = url.split('/', 3)[:3]  # https://archi.kumoh.ac.kr
                        base = "/".join(site_root)
                        full = base + href
                    elif href.startswith('?'):
                        full = url.split('?')[0] + href
                    else:
                        full = url.rsplit('/', 1)[0] + '/' + href

                    article_links.append(full)

            if not article_links:
                logger.warning(f"❌ 게시글을 찾지 못함: {url}")
                return False

            latest_url = article_links[0]
            logger.info(f"   📌 최신 게시글: {latest_url}")

            # 이미 크롤링한 경우 스킵
            if latest_url in self.existing_urls:
                logger.info(f"   ⏭️ 최신 게시글 이미 크롤링됨 → 스킵")
                self.stats["skipped"] += 1
                return False

            # 최신 게시글 크롤링
            page_info = {
                "url": latest_url,
                "name": f"{name} (최신 게시글)",
                "page_type": "board_notice",
                "board_name": name,                
            }
            success = self.crawl_url(latest_url, page_info)

            if success:
                self.existing_urls.add(latest_url)

            return success

        except Exception as e:
            logger.error(f"❌ 교육과정 게시판 최신글 크롤링 실패: {e}")
            return False


    def run(self):
        """정적 페이지 크롤링 실행"""
        print("=" * 80)
        print("departmentCrawler 시작 (학과/동아리/정적 소개 페이지)")
        print("=" * 80)
        print(f"대상 URL 수: {len(self.department_static_urls)}")
        print("=" * 80)

        start_time = datetime.now()

        # 1) 정적 페이지(학과/동아리 소개 등)
        for page in self.department_static_urls:
            print(f"\n📍 대상 사이트 이름 : [{page['name']}]")
            print("-" * 80)
            self.crawl_url(page['url'], page)
            import time
            time.sleep(0.5)

        # 2) 학과별 교육과정 게시판(최신글 1개씩)
        print("\n" + "=" * 80)
        print("📘 학과별 교육과정 게시판 최신글 크롤링")
        print("=" * 80)

        for board in self.department_board_urls:
            print(f"\n📍 대상 게시판 이름 : [{board['name']}]")
            print("-" * 80)
            self.crawl_latest_from_department_board(board)
            import time
            time.sleep(0.5)

        # 인덱스 저장
        if self.saved_pages:
            index_data = {
                "crawl_date": datetime.now().isoformat(),
                "total_pages": len(self.saved_pages),
                "pages": self.saved_pages,
            }
            self.storage.save_index(index_data)
            logger.info(f"\n📚 first 인덱스 저장 완료: {len(self.saved_pages)} 페이지")

        elapsed = datetime.now() - start_time

        print("\n" + "=" * 80)
        print("departmentCrawler 크롤링 완료!")
        print("=" * 80)
        print(f"총 시도: {self.stats['total']}")
        print(f"성공: {self.stats['success']}")
        print(f"건너뜀 (이미 크롤링됨): {self.stats['skipped']}")
        print(f"실패: {self.stats['failed']}")
        print(f"필터됨: {self.stats['filtered']}")
        print(f"\n📎 첨부파일:")
        print(f"  - 발견됨: {self.stats['attachments_found']}개")
        if self.enable_minio:
            print(f"  - MinIO 업로드 성공: {self.stats['attachments_uploaded']}개")
        else:
            print(f"  - 메타데이터만 기록 (MinIO 비활성화)")
        print(f"\n소요 시간: {elapsed}")
        print("=" * 80)

        output_dir = Path(__file__).parent.parent / "data" / "first_crawled"
        print(f"\n📂 결과 저장 위치: {output_dir}")
        print(f"   - 페이지: {output_dir}/pages/")
        print(f"   - 인덱스: {output_dir}/crawl_index.json")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='departmentCrawler - 학과/동아리/소개 페이지 1회성 크롤러')
    parser.add_argument('--enable-minio', action='store_true',
                        help='첨부파일을 MinIO에 업로드 (기본값: 메타데이터만 기록)')
    args = parser.parse_args()

    crawler = departmentCrawler(enable_minio=args.enable_minio)
    crawler.run()


if __name__ == "__main__":
    main()
