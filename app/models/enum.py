from enum import Enum

class Language(str, Enum):
    KOR = "KOR"
    ENG = "ENG"

class AnalysisStatus(str, Enum):
    NOT_ANALYZED = "NOT_ANALYZED"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Tier(str, Enum):
    FREE = "FREE"
    PAID = "PAID"

class Role(str, Enum):
    ROLE_USER = "ROLE_USER"
    ROLE_ADMIN = "ROLE_ADMIN"

class Quarter(str, Enum):
    Q1 = "1Q"
    Q2 = "2Q"
    Q3 = "3Q"
    Q4 = "4Q"

class FormType(str, Enum):
    REGULAR_10_K = "REGULAR_10_K"
    REGULAR_10_Q = "REGULAR_10_Q"
    AMENDMENT_10_K_A = "AMENDMENT_10_K_A"
    AMENDMENT_10_Q_A = "AMENDMENT_10_Q_A"

class FilingItem(str, Enum):
    ITEM_1A = "ITEM_1A"  # Risk Factors
    ITEM_7 = "ITEM_7"    # MD&A
    ITEM_8 = "ITEM_8"    # Financial Statements

class DcfMetric(str, Enum):
    FCFE_GROWTH_RATE = "FCFE_GROWTH_RATE"
    CAPEX_TO_REVENUE = "CAPEX_TO_REVENUE"
    NET_BORROWING_RATE = "NET_BORROWING_RATE"

class AuthProvider(str, Enum):
    GOOGLE = "GOOGLE"
    NAVER = "NAVER"

