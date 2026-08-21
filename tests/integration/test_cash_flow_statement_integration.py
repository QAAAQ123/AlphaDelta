from edgar.core import Quarters
import pytest
from edgar import get_by_accession_number
from app.modules.financial_extractor.cash_flow_statement import (
    _determine_quarter,
    get_items_qtd_cash_flow_statement
)
from app.models.enum import *

"""
## cash_flow_statement 통합 테스트 항목
1. 표준 결산월(12월) 10-Q,10-K: GOOGL 
2. 비표준 결산월 각각 10-Q,10-K
    - 9월 결산: APPL
    - 1월 결산: NVDA
3. 결산월 상관없이 회사의 Q1: BRK.B(0001193125-26-202243)
4. 수정 공시: TSLA
- 테스트 대상: 0001628280-25-035806(25-2Q) => 중간의 10-K/A를 건너뛰고 1Q를 선택

4. Fiscal Year 변경 이력 존재: AZPN(검증X)
- 전환 기간: 2021-10-01 - 2022-06-30
- 10-KT: 10-KT가 따로 나오기 때문에 10-KT의 값을 따로 가져와야함.
    - period_of_report: 2022-06-30
    - accession_number: 0001897982-22-000023
    - filing_date: 2022-08-29

## 검증 항목
1. Quarter가 expected한 대로 나오는지
2. getter 항목 1,2개: ocf,fcf,capex 중 2개
- get_operating_cash_flow()/get_free_cash_flow()/get_capital_expenditures()
3. 대부분의 경우에 CF의 YTD > QTD(예외 케이스는 검증하지 않음)
"""


def _make_concept_getters():
    """
    get_items_qtd_cash_flow_statement에 전달할 concept_getters 딕셔너리 반환.
    각 람다는 Financials 객체를 인자로 받는다.
    """
    return {
        # "ocf":   lambda financials: financials.get_operating_cash_flow(),
        # "fcf":   lambda financials: financials.get_free_cash_flow(),
        # "capex": lambda financials: financials.get_capital_expenditures(),
        "ocf":   lambda financials: financials.get_operating_cash_flow(),   # TODO: 메서드명 확인
        "capex": lambda financials: financials.get_capital_expenditures(),  # TODO: 메서드명 확인
    }


# ---------------------------------------------------------------------------
# 파라미터 케이스 정의
# ---------------------------------------------------------------------------

FILING_CASES = [
    # ── 1. 표준 결산월 (12월) 10-Q ──────────────────────────────────────────
    pytest.param(
        {
            "description":      "GOOGL 10-Q (2025 Q1, 12월 결산)",
            "accession_number": "0001652044-25-000043",
            "expected_quarter": Quarter.Q1,  # TODO: enum 멤버명 확인
            "check_ytd_gt_qtd": False,       # Q1은 YTD == QTD
        },
        id="googl_10q_2025q1",
    ),
    # ── 2. 표준 결산월 (12월) 10-K ──────────────────────────────────────────
    pytest.param(
        {
            "description":      "GOOGL 10-K (2024 FY, 12월 결산)",
            "accession_number": "0001652044-24-000022",
            "expected_quarter": Quarter.Q4,  # TODO: enum 멤버명 확인
            "check_ytd_gt_qtd": True,
        },
        id="googl_10k_2024fy",
    ),
    # ── 3. 비표준 결산월 9월 — AAPL 10-Q ────────────────────────────────────
    pytest.param(
        {
            "description":      "AAPL 10-Q (2024, 6월 결산)",
            "accession_number": "0000320193-24-000081",
            "expected_quarter": Quarter.Q3,  # TODO: AAPL FY2024 기준 실제 분기 확인
            "check_ytd_gt_qtd": True,
        },
        id="aapl_10q_9month_fy",
    ),
    # ── 4. 비표준 결산월 9월 — AAPL 10-K ────────────────────────────────────
    pytest.param(
        {
            "description":      "AAPL 10-K (2024 FY, 9월 결산)",
            "accession_number": "0000320193-24-000123",
            "expected_quarter": Quarter.Q4,
            "check_ytd_gt_qtd": True,
        },
        id="aapl_10k_9month_fy",
    ),
    # ── 9. 결산월 무관 Q1 — BRK.B ───────────────────────────────────────────
    pytest.param(
        {
            "description":      "BRK.B Q1 (2026)",
            "accession_number": "0001193125-26-202243",
            "expected_quarter": Quarter.Q1,
            "check_ytd_gt_qtd": False,  # Q1은 YTD == QTD
        },
        id="brkb_q1_2026",
    ),
    # ── 10. 수정 공시 — TSLA 25-2Q (10-K/A를 건너뛰고 1Q 선택 검증) ─────────
    pytest.param(
        {
            "description":      "TSLA 10-Q/A 25-2Q (중간 10-K/A 스킵 후 1Q 선택)",
            "accession_number": "0001628280-25-035806",
            "expected_quarter": Quarter.Q2,  # TODO: 실제 quarter 확인
            "check_ytd_gt_qtd": True,
        },
        id="tsla_10qa_25_2q",
    ),
]


# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", params=FILING_CASES)
def filing_case(request):
    """
    파라미터화된 케이스별로 Filing 객체를 가져온다.
    VCR 카세트는 conftest.py의 vcr_config 또는 @pytest.mark.vcr 로 제어한다.
    """
    case = request.param
    filing = get_by_accession_number(case["accession_number"])
    assert filing is not None, (
        f"[{case['description']}] accession_number={case['accession_number']} "
        "에 해당하는 Filing을 찾지 못하였습니다."
    )
    return {"filing": filing, **case}


# ---------------------------------------------------------------------------
# 테스트
# ---------------------------------------------------------------------------

@pytest.mark.vcr         
class TestDetermineQuarter:
    """_determine_quarter() 단독 검증"""

    def test_quarter_matches_expected(self, filing_case):
        """
        Filing 객체로부터 결정된 Quarter가 케이스별 expected_quarter와 일치해야 한다.
        1. Quarter가 expected한 대로 나오는지
        """
        filing = filing_case["filing"]
        expected = filing_case["expected_quarter"]

        actual = _determine_quarter(filing)

        assert actual == expected, (
            f"[{filing_case['description']}] "
            f"expected={expected}, actual={actual}"
        )


@pytest.mark.vcr
class TestGetItemsQtdCashFlowStatement:
    """get_items_qtd_cash_flow_statement() 종합 검증"""

    # ── 2-1. 반환값 구조 ────────────────────────────────────────────────────

    def test_returns_dict_with_expected_keys(self, filing_case):
        """
        반환값이 dict이고 concept_getters에 전달한 키를 포함해야 한다.
        2. getter 항목 1,2개: ocf,fcf,capex 중 2개
        """
        filing = filing_case["filing"]
        concept_getters = _make_concept_getters()

        result = get_items_qtd_cash_flow_statement(filing, concept_getters)

        assert isinstance(result, dict), (
            f"[{filing_case['description']}] 반환값이 dict가 아닙니다: {type(result)}"
        )
        for key in concept_getters.keys():
            assert key in result["values"], (
                f"[{filing_case['description']}] '{key}' 키가 결과에 없습니다. "
                f"결과 키: {list(result.keys())}"
            )

    # ── 2-2. 값 타입 및 None 검증 ───────────────────────────────────────────

    def test_values_are_numeric_and_not_none(self, filing_case):
        """
        각 concept getter의 결과가 None이 아닌 숫자(int | float)여야 한다.
        """
        filing = filing_case["filing"]
        concept_getters = _make_concept_getters()
        result = get_items_qtd_cash_flow_statement(filing, concept_getters)

        for key in concept_getters:
            value = result["values"].get(key)
            assert value is not None, (
                f"[{filing_case['description']}] '{key}' 값이 None입니다."
            )
            assert isinstance(value, (int, float)), (
                f"[{filing_case['description']}] '{key}' 값이 숫자가 아닙니다: "
                f"type={type(value)}, value={value}"
            )

    # ── 2-3. OCF 부호 검증 (운영 현금흐름은 양수가 일반적) ─────────────────

    def test_ocf_is_positive(self, filing_case):
        """
        OCF(영업현금흐름)는 대부분의 케이스에서 양수여야 한다.
        (테스트 케이스 기업들은 안정적인 대형주이므로 음수 OCF는 오류 신호)
        """
        filing = filing_case["filing"]
        concept_getters = _make_concept_getters()
        result = get_items_qtd_cash_flow_statement(filing, concept_getters)

        ocf = result["values"].get("ocf")
        if ocf is None:
            pytest.skip(f"[{filing_case['description']}] ocf 값 없음, 스킵")

        assert ocf > 0, (
            f"[{filing_case['description']}] OCF가 음수입니다: {ocf:,}"
        )

    # ── 2-4. CapEx 부호 검증 (자본지출은 음수 또는 양수 절대값) ────────────

    def test_capex_is_nonzero(self, filing_case):
        """
        CapEx는 0이 아닌 값이어야 한다.
        (부호 컨벤션은 구현마다 다를 수 있으므로 절대값만 검증)
        """
        filing = filing_case["filing"]
        concept_getters = _make_concept_getters()
        result = get_items_qtd_cash_flow_statement(filing, concept_getters)

        capex = result["values"].get("capex")
        if capex is None:
            pytest.skip(f"[{filing_case['description']}] capex 값 없음, 스킵")

        assert capex != 0, (
            f"[{filing_case['description']}] CapEx가 0입니다."
        )

    # ── 2-5. YTD > QTD 검증 ────────────────────────────────────────────────

    def test_ytd_greater_than_qtd_for_non_q1(self, filing_case):
        """
        Q1을 제외한 케이스에서 YTD OCF는 QTD OCF보다 커야 한다.
        (YTD는 연간 누적, QTD는 해당 분기만의 값)

        검증 방법:
        - get_items_qtd_cash_flow_statement()가 QTD를 반환한다고 가정
        - YTD는 Filing의 Financials에서 직접 가져온다
        3. 대부분의 경우에 CF의 YTD > QTD(예외 케이스는 검증하지 않음)  
        """
        if not filing_case["check_ytd_gt_qtd"]:
            pytest.skip(
                f"[{filing_case['description']}] Q1 케이스 — YTD==QTD이므로 스킵"
            )

        filing = filing_case["filing"]
        concept_getters = _make_concept_getters()

        # QTD 결과
        result_qtd = get_items_qtd_cash_flow_statement(filing, concept_getters)
        assert result_qtd is not None

        # YTD: current_filing의 Financials에 getter 사용
        current_financials = filing.obj().financials

        for concept, getter in concept_getters.items():
            ytd_value = getter(current_financials)
            qtd_value = result_qtd["values"].get(concept)

            if ytd_value is None or qtd_value is None:
                pytest.skip("YTD,QTD Value 없음")
                continue

            assert abs(ytd_value) >= abs(qtd_value), (
                f"[{filing_case['description']}] {concept}: "
                f"YTD({ytd_value:,.0f}) < QTD({qtd_value:,.0f}) — 예상치 못한 결과"
            )


# ---------------------------------------------------------------------------
# TSLA 수정 공시 전용 테스트
# ---------------------------------------------------------------------------

@pytest.mark.vcr
class TestTslaAmendedFiling:
    """
    TSLA 25-2Q 수정 공시:
    중간에 10-K/A가 존재하더라도 prior period로 10-Q(1Q)를 선택하는지 검증.

    이 테스트는 _find_prior_period_filing() 내부 로직을 간접 검증한다.
    (직접 호출보다 get_items_qtd_cash_flow_statement() 전체 흐름으로 검증)
    """

    TSLA_2Q25_ACCESSION = "0001628280-25-035806"

    @pytest.fixture(scope="class")
    def tsla_filing(self):
        filing = get_by_accession_number(self.TSLA_2Q25_ACCESSION)
        assert filing is not None, "TSLA 25-2Q filing을 찾지 못하였습니다."
        return filing

    def test_quarter_is_q2(self, tsla_filing):
        """TSLA 25-2Q filing의 quarter가 Q2로 판별되어야 한다."""
        actual = _determine_quarter(tsla_filing)
        assert actual == Quarter.Q2, f"expected=Q2, actual={actual}"

    def test_result_is_computable(self, tsla_filing):
        """
        수정 공시임에도 QTD 계산이 정상 완료되어야 한다.
        (10-K/A를 prior로 잘못 선택하면 계산 실패 또는 잘못된 값 반환)
        """
        concept_getters = _make_concept_getters()
        result = get_items_qtd_cash_flow_statement(tsla_filing, concept_getters)

        assert result is not None
        for key in concept_getters:
            assert result["values"].get(key) is not None, (
                f"TSLA 25-2Q: '{key}' 값이 None — "
                "10-K/A를 prior로 선택했을 가능성 확인 필요"
            )