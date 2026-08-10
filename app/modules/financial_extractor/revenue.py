"""
매출(revenue or net income) QTD 계산 모듈
- 매출은 손익계산서의 항목이여서 단순 getter를 해주면 QTD 값을 얻을 수 있다.
Edgartools
1순위-표준화 컨셉. result = self._get_standardized_concept_by_xbrl('income',['Contract Revenue', 'Revenue'],period_offset)
Fallback-라벨 기반 검색. self._get_standardized_concept_value('income', patterns, period_offset)
=> 여기서 메타 데이터(dataframe의 header)의 최신 날짜이면서 days가 짧은 순으로 정렬한다.
예시: 티커-O (리얼리티 인컴)
- 1Q: Three months ended(당년도,직전년도)
- 2Q: Three months ended(당년도,직전년도)와 Six months ended(당년도,직전년도)
- 3Q: Three months ended(당년도,직전년도)와 Nine months ended(당년도,직전년도)
- 4Q(10-K): Years ended(당년도,직전년도,전전년도)
"""
from ast import Tuple

from edgar import Filing
import pandas as pd
from edgar.financials import _NON_PERIOD_COLUMNS, _order_period_columns
from app.core import logger
"""
{
    "workbench.startupEditor": "none",
    "workbench.secondarySideBar.defaultVisibility": "hidden",
    "editor.fontSize": 17,
    "liveServer.settings.donotShowInfoMsg": true,
    "files.autoGuessEncoding": true,
    "explorer.confirmDelete": false,
    "workbench.tree.indent": 14,
    "editor.inlineSuggest.edits.allowCodeShifting": "never",
    "workbench.editor.empty.hint": "hidden",
    "editor.quickSuggestions": {

        "other": "on",
        "comments": "off",
        "strings": "on"
    },
    "editor.suggestOnTriggerCharacters": true,
    "editor.suggestSelection": "recentlyUsedByPrefix",
    "editor.inlineSuggest.enabled": false,
    "extensions.ignoreRecommendations": true,
    "terminal.integrated.initialHint": false,
    "terminal.integrated.fontSize": 18,
    "editor.fontLigatures": false,
    "window.zoomLevel": 1,
    "explorer.confirmDragAndDrop": false,
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": false,
    "python.analysis.autoImportCompletions": true,
    "remote.autoForwardPortsSource": "hybrid",
    "editor.lineHeight": 1.6,          
    "editor.cursorBlinking": "smooth",
    "workbench.iconTheme": "material-icon-theme",
    "workbench.colorTheme": "Nord Frost",
    "telemetry.telemetryLevel": "off",
    "git.autofetch": true,
    "http.proxySupport": "off",
    "extensions.autoCheckUpdates": false,
    "chat.viewSessions.orientation": "stacked",
    "workbench.preferredHighContrastColorTheme": "Nord Frost",
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": [
        "tests"
    ]
}
"""
def get_revenue_qtd():
    """filing에서 매출(Revenue) QTD 값을 추출하고, 해당 값이 실제 QTD(120일 이하)인지 검증합니다."""
    pass

def _get_income_statement(filing: Filing) -> pd.DataFrame| None:
    """
    책임1. Filing 객체에서 손익계산서를 추출 및 Dataframe으로 render
    Args:
        filing: edgartools Filing 타입
    Returns:
        pd.DataFrame: IS가 있는 경우
        None: IS가 없는 경우
    Raises:
        주요 Error 없음
    """
    financials = filing.obj().financials
     
    if financials is None:
        return None
     
    income_statement = financials.income_statement()
    return income_statement.render(standard=True).to_dataframe()

def _extract_primary_period_meta_data(income_statment: pd.DataFrame) -> Tuple | None:
    """
    책임2-손익계산서 DataFrame를 우선순위대로 정렬하여 가장 최신이고 days가 짧은 meata data 추출
    Args:
        income_statement: 손익계산서 edgartools 표준화 Dataframe
    Returns:
        target_period_meta_data: 가장 최신이고 days가 짧은 곳의 메타 데이터
    Raise:
    """
    if income_statment is None:
        return None

    period_columns = [col for col in income_statment not in _NON_PERIOD_COLUMNS]
    period_columns = _order_period_columns()