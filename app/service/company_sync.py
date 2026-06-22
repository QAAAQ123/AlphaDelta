import uuid
import pandas as pd
import json
import urllib.request
from loguru import logger
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
app_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if app_root not in sys.path:
    sys.path.insert(0, app_root)

def get_nasdaq100_index_companies() -> list[str]:

    request_id = str(uuid.uuid4())[:8]

    try:
        with logger.contextualize(ticker="INDEX", request_id=request_id):
            wikipedia_nasdaq_100_url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            logger.info("나스닥 100 지수 구성 기업 위키피디아 크롤링 시작")
            
            req = urllib.request.Request(
                wikipedia_nasdaq_100_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            html_content = urllib.request.urlopen(req).read()
            
            try:
                tables = pd.read_html(html_content, match="Ticker")
            except ValueError:
                tables = pd.read_html(html_content, match="Symbol")
                
            if not tables:
                raise ValueError("위키백과에서 구성 종목 테이블을 필터링하지 못했습니다.")
            
            # 3. 매칭된 첫 번째 테이블 선택 후 컬럼 처리
            target_df = tables[0]
            orig_cols = target_df.columns
            
            ticker_col = next((c for c in orig_cols if 'TICKER' in str(c).upper() or 'SYMBOL' in str(c).upper()), None)
            company_col = next((c for c in orig_cols if 'COMPANY' in str(c).upper() or 'NAME' in str(c).upper()), None)
            industry_col = next((c for c in orig_cols if 'ICB INDUSTRY' in str(c).upper() or 'INDUSTRY' in str(c).upper()), None)
            subsector_col = next((c for c in orig_cols if 'ICB SUBSECTOR' in str(c).upper() or 'SUBSECTOR' in str(c).upper()), None)

            if not all([ticker_col, company_col, industry_col, subsector_col]):
                raise KeyError("필요한 컬럼(Ticker, Company, Industry, Subsector) 중 일부를 찾을 수 없습니다.")

            logger.info("모든 대상 컬럼 탐색 성공. 데이터 가공을 시작합니다.")

            # 4. 필요한 컬럼만 추출하고 깔끔한 이름으로 리네임
            refined_df = target_df[[ticker_col, company_col, industry_col, subsector_col]].copy()
            refined_df.columns = ['ticker', 'company', 'industry', 'subsector']
            
            # 문자열 데이터 공백 및 특수 가공 처리
            for col in refined_df.columns:
                refined_df[col] = refined_df[col].astype(str).str.strip()

            # 5. 상용 DB 적재나 API 결과 서빙에 용이하도록 딕셔너리 리스트(JSON 형태)로 변환
            return refined_df.to_dict(orient="records")
                
    except Exception as e:
        logger.error(f"Data fetching/parsing failed: {e}")
        return []
    

if __name__ == "__main__":
    try:
        result = get_nasdaq100_index_companies()
        print(f"✅ [성공] 가져온 데이터 개수: {len(result)}개")
        print("📋 [샘플 데이터 상위 2개]:")
        print(json.dumps(result))
    except Exception as e:
        print(f"❌ [실패] 에러 발생: {e}")