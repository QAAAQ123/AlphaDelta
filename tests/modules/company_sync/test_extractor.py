"""
exactor 단위 테스트 항목
1. extract_and_clean_df
    에러
    1. html_content가 None/잘못된 html -> 예외가 발생했을 때 except Exception이 잡아서 [] 리턴
    2. tables가 빈 테이블 ->  예외가 발생했을 때 exception이 잡아서 [] return
    3. mock col_mapping에 None 포함 -> [] 리턴
    정상
    1. list[dict] 리턴
2. fetch_nasdaq100_via_wikipedia
    에러
    1. 네트워크 실패 시 -> None 리턴
3. _find_column_mapping
    에러
    1. original_columns가 empty -> None 리턴
    2. 일부 컬럼만 없음 -> 해당 키만 None으로 리턴
    정상
    1. original_columns가 정상 인자일 때 -> dict[str,str] 리턴
    2. 컬럼명 변형('Symbol'이나 'ICB Industry')로 변형 -> fallback 매핑 성공
4. _clean_dataframe
    예외
    1. 컬럼에 NaN이 있을 때 -> ""로 바뀌고 DataFrame 리턴
    정상
    1. 정상 인자가 들어올 때 -> DataFrame 리턴
    2. 띄어쓰기가 들어가 있을 때 strip()로 제거 후 -> DataFrame리턴
"""

import pytest
import urllib.error
import pandas as pd
from app.modules.company_sync.extractor import _clean_dataframe,_find_column_mapping, extract_and_clean_df,fetch_nasdaq100_via_wikipedia

@pytest.fixture
def column_mapping():
    return { 
		'ticker': 'Ticker', 
		'company': 'Company', 
		'industry': 'Industry', 
		'subsector': 'Subsector', 
	}

class TestCleanDataframe:
    """_clean_dataframe 단위 테스트"""
    #_clean_dataframe 단위 테스트
    def test_clean_dataframe_replace_nan_with_empty_string(self, column_mapping):
        """에러1. 컬럼에 NaN이 있을 때 -> ""로 바뀌고 DataFrame 리턴"""
        #given-상황
        df = pd.DataFrame({
            'Ticker': ['AAPL','GOOGL'],
            'Company': ["Apple Inc.", None],
            'Industry': ['Technology', 'Tech'],
            'Subsector': [None, 'Search'],
        })

        #when-실행
        result = _clean_dataframe(df,column_mapping)

        #then-결과 확인
        assert result.iloc[1]['company'] == ''
        assert result.iloc[0]['subsector'] == ''

    def test_clean_dataframe_returns_expected_columns(self, column_mapping):
        """1. 정상 인자가 들어올 때 -> DataFrame 리턴"""
        #given-상황
        df = pd.DataFrame({
            'Ticker': ['AAPL','GOOGL'],
            'Company': ["Apple Inc.", 'Alphabet Inc.'],
            'Industry': ['Technology', 'Tech'],
            'Subsector': ['Hardware', 'Search'],
        })

        #when-실행
        result = _clean_dataframe(df, column_mapping)

        #then-결과 확인
        # 1. 컬럼명이 정해진 key 값으로 잘 변경되었는지 확인
        assert list(result.columns) == ['ticker', 'company', 'industry', 'subsector']
        
        # 2. 데이터 개수(행)가 2개인지 확인
        assert len(result) == 2
        
        # 3. 각 컬럼의 데이터가 순서대로 잘 들어갔는지 확인
        assert result['ticker'].tolist() == ['AAPL', 'GOOGL']
        assert result['company'].tolist() == ['Apple Inc.', 'Alphabet Inc.']
        assert result['industry'].tolist() == ['Technology', 'Tech']
        assert result['subsector'].tolist() == ['Hardware', 'Search']

    def test_clean_dataframe_with_spacing_returns_expected_columns(self,column_mapping):
        """정상2. 양쪽 끝의 띄어쓰기가 들어가 있을 때 strip()로 제거 후 -> DataFrame리턴"""
        # given-상황
        df = pd.DataFrame({
            'Ticker': ['    AAPL  ', '  GOOGL  '],
            'Company': ['   Apple Inc.  ', '   Alphabet Inc.  '],
            'Industry': ['   Technology  ', '   Tech  '],
            'Subsector': ['   Hardware  ', '   Search  '],
        })

        #when-실행
        result = _clean_dataframe(df, column_mapping)

        #then-결과 확인
        # 1. 컬럼명이 정해진 key 값으로 잘 변경되었는지 확인
        assert list(result.columns) == ['ticker', 'company', 'industry', 'subsector']
        
        # 2. 데이터 개수(행)가 2개인지 확인
        assert len(result) == 2
        
        # 3. 각 컬럼의 데이터가 순서대로 잘 들어갔는지 확인
        assert result['ticker'].tolist() == ['AAPL', 'GOOGL']
        assert result['company'].tolist() == ['Apple Inc.', 'Alphabet Inc.']
        assert result['industry'].tolist() == ['Technology', 'Tech']
        assert result['subsector'].tolist() == ['Hardware', 'Search']
    
class TestFetchNasdaq100ViaWikipedia:
    """fetch_nasdaq100_via_wikipedia 단위 테스트"""
    def test_fetch_nasdaq100_via_wikipedia_with_http_request_error_returns_none(self,mocker):
        """에러1. 네트워크 연결 실패시 -> None 리턴"""
        #given-상황
        mock_urlopen = mocker.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection timeout")
        )

        #when-실행
        result = fetch_nasdaq100_via_wikipedia()

        #then-결과 확인
        assert result is None
        mock_urlopen.assert_called_once()

class TestFindColumnMapping:
    """_find_column_mapping 단위 테스트"""
    def test_find_column_mapping_with_empty_columns_returns_dict_with_all_none(self):
        """에러1. original_columns가 empty -> None 리턴"""
        #given-상황
        original_columns = []

        #when-실행
        result = _find_column_mapping(original_columns)

        #then-결과 확인
        assert result == {
            'ticker': None, 
            'company': None, 
            'industry': None, 
            'subsector': None
        }

    def test_find_column_mapping_with_partial_columns_returns_partial_none(self):
        """에러2. 일부 컬럼만 없음 -> 해당 키만 None으로 리턴"""
        #given-상황
        original_columns = ['TICKER','COMPANY','ICB INDUSTRY']

        #when-실행
        result = _find_column_mapping(original_columns)

        #then-결과 확인
        assert result == {
            'ticker': 'TICKER', 
            'company': 'COMPANY', 
            'industry': 'ICB INDUSTRY', 
            'subsector': None
        }
    
    def test_find_column_mapping_returns_expected_dict(self):
        """정상1. original_columns가 정상 인자일 때 -> dict[str,str] 리턴"""
        #given-상황
        original_columns = ['TICKER','COMPANY','ICB INDUSTRY','ICB SUBSECTOR']

        #when-실행
        result = _find_column_mapping(original_columns)

        #then-결과 확인
        assert result == {
            'ticker': 'TICKER', 
            'company': 'COMPANY', 
            'industry': 'ICB INDUSTRY', 
            'subsector': 'ICB SUBSECTOR'
        }

    def test_find_column_mapping_with_fallback_logic_returns_expected_dict(self):
        """ 2. 컬럼명 변형('Symbol'이나 'ICB Industry')로 변형 -> fallback 매핑 성공"""
         #given-상황
        original_columns = ['symbol','COMPANY','icb industry','ICB subsector']

        #when-실행
        result = _find_column_mapping(original_columns)

        #then-결과 확인
        assert isinstance(result, dict)
        assert result == {
            'ticker': 'symbol', 
            'company': 'COMPANY', 
            'industry': 'icb industry', 
            'subsector': 'ICB subsector'
        }

class TestExtractAndCleanDf:
    """extract_and_clean_df 단위 테스트"""
    @pytest.mark.parametrize(
            "html_content",
            [
                # 케이스 1: None 데이터가 들어온 경우 (read_html에서 TypeError 발생)
                None,
                # 케이스 2: 아예 비어있는 HTML인 경우 (read_html에서 ValueError 발생)
                b"",
                b"<html><body><h1>No Table Here</h1></body></html>",
                # 케이스 3: 테이블은 있으나 "Ticker" 문자열이 없어 테이블 자체를 필터링하지 못하는 경우
                b"""
                <html>
                <body>
                    <table>
                        <thead>
                            <tr><th>Symbol</th><th>Company Name</th></tr>
                        </thead>
                        <tbody>
                            <tr><td>AAPL</td><td>Apple</td></tr>
                        </tbody>
                    </table>
                </body>
                </html>
                """
            ]
        )
    def test_extract_and_clean_df_with_none_or_wrong_html(self, html_content):
        """에러1. html_content가 None/잘못된 html -> 예외가 발생했을 때 except Exception이 잡아서 [] 리턴"""
        #when-실행
        result = extract_and_clean_df(html_content)

        #then-결과 확인
        assert result == []
        assert isinstance(result, list)

    def test_extract_and_clean_df_with_empty_tables(self):
        """에러2. tables가 빈 테이블 ->  예외가 발생했을 때 exception이 잡아서 [] return"""
        #given-상황
        html_content = b"""<html><body><div></div></body></html>"""

        #when-실행
        result = extract_and_clean_df(html_content)

        #then-결과 확인
        assert result == []
        assert isinstance(result, list)
        
    def test_extract_and_clean_df_with_col_mapping_contains_none(self):
        """에러3. column_mapping에 None 포함 -> [] 리턴"""
        #given-상황
        html_content = b"""
            <html>
            <body>
                <table class="wikitable">
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th>Company</th>
                            <th>Industry</th>
                            <th>WrongColumnName</th> 
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>AAPL</td>
                            <td>Apple Inc.</td>
                            <td>Technology</td>
                            <td>SomeValue</td>
                        </tr>
                    </tbody>
                </table>
            </body>
            </html>
            """
        #when-실행
        result = extract_and_clean_df(html_content)

        #then-결과 검증
        assert result == []
        assert isinstance(result, list)

    def test_extract_and_clean_df_returns_expected_list(self):
        """정상1. list[dict] 리턴"""
        # given-상황
        html_content = b"""
        <html>
        <body>
            <table class="wikitable sortable">
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Company</th>
                        <th>ICB Industry[1]</th>
                        <th>ICB Subsector[1]</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>BKNG</td>
                        <td>Booking Holdings</td>
                        <td>Consumer Discretionary</td>
                        <td>Transportation Services</td>
                    </tr>
                    <tr>
                        <td>NVDA</td>
                        <td>Nvidia</td>
                        <td>Technology</td>
                        <td>Semiconductors</td>
                    </tr>
                    <tr>
                        <td>MSFT</td>
                        <td>Microsoft</td>
                        <td>Technology</td>
                        <td>Software</td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """

        #when-실행
        result = extract_and_clean_df(html_content)

        #given-결과 확인
        assert isinstance(result, list)
        assert all(isinstance(row, dict) for row in result)
        assert all(isinstance(val, str) for row in result for val in row.values())

        assert len(result) == 3
        assert result == [
            {
                'ticker': 'BKNG', 
                'company': 'Booking Holdings', 
                'industry': 'Consumer Discretionary', 
                'subsector': 'Transportation Services'
            },
            {
                'ticker': 'NVDA', 
                'company': 'Nvidia', 
                'industry': 'Technology', 
                'subsector': 'Semiconductors'
            },
            {
                'ticker': 'MSFT', 
                'company': 'Microsoft', 
                'industry': 'Technology', 
                'subsector': 'Software'
            }
        ]