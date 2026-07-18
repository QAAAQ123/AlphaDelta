import io
import pandas as pd
import urllib.request
from loguru import logger


def fetch_nasdaq100_via_wikipedia() -> bytes | None:
    """
    위키피디아 나스닥 100 종목을 크롤링해서 bytes 형태의 HTML로 반환하는 함수
    """
    try:
        with logger.contextualize(ticker="NASDAQ INDEX",domain="Company"):
            wikipedia_nasdaq_100_url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            logger.info("나스닥 100 지수 구성 기업 위키피디아 크롤링 시작")
            
            req = urllib.request.Request(
                wikipedia_nasdaq_100_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            return urllib.request.urlopen(req).read()
    except Exception as e:
        logger.warning(f"위키피티아 크롤링 실패 None 리턴: {e}")
        return None

def extract_and_clean_df(html_content: bytes) -> list[dict]:
    """
    크롤링으로 받아온 나스닥 100 html을
    ['ticker', 'company', 'industry', 'subsector']
    dict 형태로 정리해주는 함수
    """
    try:
        tables = pd.read_html(io.BytesIO(html_content), match="Ticker")
        if not tables:
            raise ValueError("위키백과에서 구성 종목 테이블을 필터링 실패")

        target_df = tables[0]
        col_mapping = _find_column_mapping(target_df.columns)

        if not all(col_mapping.values()):
            raise KeyError("필요한 컬럼(Ticker, Company, Industry, Subsector) 중 일부를 찾을 수 없음")

        logger.info("나스닥 100 지수 구성 기업 컬럼 탐색 성공. 데이터 가공 시작")

        refined_df = _clean_dataframe(target_df, col_mapping)
        return refined_df.to_dict(orient="records")

    except Exception as e:
        logger.error(f"데이터 fetching/parsing 실패: {e}")
        return []

def _find_column_mapping(original_columns: list) -> dict[str,str | None]:
    """실제 컬럼명을 찾아 매핑(TICKER/SYMBOL, COMPANY/NAME, ICB INDUSTRY/INDUSTRY, ICB SUBSECTOR/SUBSECTOR)"""
    return {
        'ticker': next((c for c in original_columns if 'TICKER' in str(c).upper() or 'SYMBOL' in str(c).upper()), None),
        'company': next((c for c in original_columns if 'COMPANY' in str(c).upper() or 'NAME' in str(c).upper()), None),
        'industry': next((c for c in original_columns if 'ICB INDUSTRY' in str(c).upper() or 'INDUSTRY' in str(c).upper()), None),
        'subsector': next((c for c in original_columns if 'ICB SUBSECTOR' in str(c).upper() or 'SUBSECTOR' in str(c).upper()), None),
    }


def _clean_dataframe(dataframe: pd.DataFrame, column_mapping: dict[str,str]) -> pd.DataFrame:
    """필요한 컬럼만 추출, 컬럼명 재작성,NaN 정제"""
    refined_df = dataframe[list(column_mapping.values())].copy()
    refined_df.columns = list(column_mapping.keys())

    refined_df = refined_df.fillna("")

    for col in refined_df.columns:
        refined_df[col] = refined_df[col].astype(str).str.strip()


    return refined_df
