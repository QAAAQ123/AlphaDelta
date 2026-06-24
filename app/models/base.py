from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Float, BigInteger, Boolean, 
    DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index
)
from sqlalchemy.orm import declarative_base, relationship, declared_attr
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

# ==========================================
# 1. Python 내장 Enum 정의 (Pydantic 호환용 str 상속)
# ==========================================

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


# ==========================================
# 2. 공통 타임스탬프 믹스인 (Timezone-aware 표준 반영)
# ==========================================

class TimestampMixin:
    """데이터 생성 및 수정 이력을 추적하기 위한 최신 UTC 표준 믹스인"""
    @declared_attr
    def created_at(cls):
        return Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True), 
            default=lambda: datetime.now(timezone.utc), 
            onupdate=lambda: datetime.now(timezone.utc), 
            nullable=False
        )


# ==========================================
# 3. 도메인 엔티티 모델 (RDBMS 스키마 세부 구현)
# ==========================================

class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    ticker = Column(String(10), nullable=False, unique=True, index=True)
    cik = Column(String(10), nullable=False, unique=True, index=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

    # 관계 설정 (Company ↔ Filing 양방향 1:N)
    filings = relationship("Filing", back_populates="company", cascade="all, delete-orphan")
    # 관계 설정 (Company ↔ UserWatchlistSlot 양방향 1:N)
    user_watchlist_slots = relationship("UserWatchlistSlot", back_populates="company", cascade="all, delete-orphan")


class Filing(Base, TimestampMixin):
    __tablename__ = "filings"

    id = Column(Integer, primary_key=True, index=True)
    accession_number = Column(String(50), nullable=False, unique=True)
    form_type = Column(SQLEnum(FormType), nullable=False)
    filing_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    primary_document = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False)
    quarter = Column(SQLEnum(Quarter), nullable=False)
    analysis_status = Column(SQLEnum(AnalysisStatus), default=AnalysisStatus.NOT_ANALYZED, nullable=False)

    # 외래키 (Company 및 자기 참조 정정공시 체인)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    amends_filing_id = Column(Integer, ForeignKey("filings.id", ondelete="SET NULL"), nullable=True)

    # 양방향 관계 정의
    company = relationship("Company", back_populates="filings")
    finance = relationship("Finance", back_populates="filing", uselist=False, cascade="all, delete-orphan")
    periodic_filing_analyses = relationship("PeriodicFilingAnalysis", back_populates="filing", cascade="all, delete-orphan")
    dcfs = relationship("Dcf", back_populates="filing", cascade="all, delete-orphan")
    filing_view_histories = relationship("FilingViewHistory", back_populates="filing", cascade="all, delete-orphan")

    # 자기 참조 (10-K/A 정정 공시 연결 관계)
    original_filing = relationship("Filing", remote_side=[id],foreign_keys=[amends_filing_id], backref="amendments") #amendments: 수정 사항


class PeriodicFilingAnalysis(Base, TimestampMixin):
    __tablename__ = "periodic_filing_analyses"

    id = Column(Integer, primary_key=True, index=True)
    part = Column(String(50), nullable=False)
    item = Column(SQLEnum(FilingItem), nullable=False)
    difference = Column(String, nullable=False)  # Text 대형 데이터 대응-PostgreSQL에서는 Text와 String의 처리 방식이 같음
    context = Column(String, nullable=False)     # Text 대형 데이터 대응
    language = Column(SQLEnum(Language), nullable=False)

    # 외래키 및 양방향 관계 설정 (Filing ↔ PeriodicFilingAnalysis)
    filing_id = Column(Integer, ForeignKey("filings.id", ondelete="CASCADE"), nullable=False)
    filing = relationship("Filing", back_populates="periodic_filing_analyses")


class Finance(Base, TimestampMixin):
    __tablename__ = "finances"

    id = Column(Integer, primary_key=True, index=True)
    ocf = Column(BigInteger, nullable=False)       
    capex = Column(BigInteger, nullable=False)     
    net_borrowing = Column(BigInteger, nullable=False)
    beta = Column(Float, nullable=True) #yfinace에서 beta return이 null일 가능성 있음  
    stock_price = Column(Float, nullable=False)    
    diluted_shares_outstanding = Column(BigInteger, nullable=False)
    basic_shares_outstanding = Column(BigInteger, nullable=False)
    raw_finances = Column(JSONB, nullable=True)    

    # 외래키 및 양방향 1:1 제약 설정
    filing_id = Column(Integer, ForeignKey("filings.id", ondelete="CASCADE"), nullable=False, unique=True)
    filing = relationship("Filing", back_populates="finance")


class Dcf(Base, TimestampMixin):
    __tablename__ = "dcfs"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(SQLEnum(DcfMetric), nullable=False)
    median_value = Column(Float, nullable=False)
    median_ci_lower = Column(Float, nullable=False)
    median_ci_upper = Column(Float, nullable=False)
    sample_size = Column(Integer, nullable=False)
    bootstrap_replications = Column(Integer, nullable=False)
    confidence_level = Column(Float, default=0.95, nullable=False)

    # 외래키 및 관계 설정
    filing_id = Column(Integer, ForeignKey("filings.id", ondelete="CASCADE"), nullable=False)
    filing = relationship("Filing", back_populates="dcfs")

    # 복합 유니크 제약조건 (한 공시당 지표별 통계 데이터 단 하나만 적재 보장)
    __table_args__ = (
        UniqueConstraint('filing_id', 'metric_name', name='unique_dcf_metric'),
    )


class DiscountRate(Base, TimestampMixin):
    __tablename__ = "discount_rates"

    id = Column(Integer, primary_key=True, index=True)
    risk_free_rate = Column(Float, nullable=False)
    average_market_return = Column(Float, nullable=False)
    year = Column(Integer, nullable=False)
    quarter = Column(SQLEnum(Quarter), nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    tier = Column(SQLEnum(Tier), default=Tier.FREE, nullable=False)
    role = Column(SQLEnum(Role), default=Role.ROLE_USER, nullable=False)
    provider = Column(SQLEnum(AuthProvider), nullable=False)
    
    # 무료 회원의 관심 종목 월별 교체 횟수 제한 필드-매월 교체 기회 2번 제공
    monthly_slot_switch_count = Column(Integer, default=0, nullable=False)
    
    # 구독 결제 관련 타임스탬프 (시간대 인식 필수)
    paid_datetime = Column(DateTime(timezone=True), nullable=True)
    next_payment_day = Column(DateTime(timezone=True), nullable=True)
    
    # 약관 동의 및 법적 리스크 방어 이력 필드
    termsVersion = Column(String(50), nullable=False)
    terms_of_service = Column(Boolean, default=False, nullable=False)
    privacy_policy = Column(Boolean, default=False, nullable=False)
    marketing_and_alerts = Column(Boolean, default=False, nullable=False)
    required_terms_agreed_at = Column(DateTime(timezone=True), nullable=False)

    user_watchlist_slots = relationship("UserWatchlistSlot", cascade="all, delete-orphan")
    user_valuation_scenarios = relationship("UserValuationScenario", cascade="all, delete-orphan")
    filing_view_histories = relationship("FilingViewHistory", cascade="all, delete-orphan")


class FilingViewHistory(Base):
    __tablename__ = "filing_view_histories"

    id = Column(Integer, primary_key=True, index=True)
    view_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # 외래키 설정
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filing_id = Column(Integer, ForeignKey("filings.id", ondelete="CASCADE"), nullable=False)

    # 방향성 반영: Filing 측면만 양방향 바인딩 지원
    filing = relationship("Filing", back_populates="filing_view_histories")

    # 복합 유니크 키 지정
    __table_args__ = (
        UniqueConstraint('user_id', 'filing_id', name='unique_user_filing_view_history'),
    )


class UserWatchlistSlot(Base, TimestampMixin):
    __tablename__ = "user_watchlist_slots"

    id = Column(Integer, primary_key=True, index=True)
    is_alarm_enable = Column(Boolean, default=True, nullable=False)

    # 외래키 설정
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    # 관계 설정 (Company ↔ UserWatchlistSlot 양방향 1:N 바인딩)
    company = relationship("Company", back_populates="user_watchlist_slots")

    # 비즈니스 제약 사양: 중복 등록 방지 복합 유니크 키 및 인덱스 배치
    __table_args__ = (
        UniqueConstraint('user_id', 'company_id', name='unique_user_company_watchlist_slot'),
        Index('index_watchlist_user_id', 'user_id')
    )


class UserValuationScenario(Base, TimestampMixin):
    __tablename__ = "user_valuation_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    
    parameters = Column(JSONB, nullable=False)

    # 단방향 외래키 배치 (User -> Scenario 1:N / Company -> Scenario 1:N)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)


    __table_args__ = (
        UniqueConstraint('user_id', 'company_id', name='unique_user_company_valuation_scenario'),
    )