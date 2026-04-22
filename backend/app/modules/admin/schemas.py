"""Pydantic response schemas for admin API endpoints.

Phase 6: Admin & Analytics
Requirements: ADMIN-01 (analytics), ADMIN-02 (user/org management)

Defines response models for:
- Analytics KPI metrics
- Paginated user list
- Paginated organization list with user counts
- Recent activity with issue counts
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


class AnalyticsResponse(BaseModel):
    """KPI metrics response for admin dashboard.

    Fields:
        total_users: All users (all time)
        active_users: Users with at least 1 analysis_run in period
        total_analyses: Count of analysis_runs in period
        documents_processed: Distinct documents with succeeded runs in period
    """
    total_users: int
    active_users: int
    total_analyses: int
    documents_processed: int


class UserItem(BaseModel):
    """Single user item for users list."""
    user_id: UUID
    email: str
    role: str
    last_login_at: Optional[datetime]
    created_at: datetime
    analysis_count: int = 0
    institution: Optional[str] = None


class UsersListResponse(BaseModel):
    """Paginated list of users response.

    Fields:
        users: List of user items
        total: Total number of users (for pagination)
        page: Current page number (1-indexed)
        page_size: Items per page
        total_pages: Total number of pages
    """
    users: list[UserItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ActivityItem(BaseModel):
    """Single activity item for recent activity list.

    Fields:
        run_id: Analysis run UUID
        user_email: Email of user who initiated the analysis
        document_name: Original filename (nullable if not available)
        started_at: When the analysis started
        status: Run status (queued, running, succeeded, failed)
        issue_count: Number of findings from this run
    """
    run_id: UUID
    user_email: str
    document_name: Optional[str]
    started_at: datetime
    status: str
    issue_count: int


class ActivityResponse(BaseModel):
    """Paginated recent activity response.

    Fields:
        activity: List of activity items
        total: Total number of activity records (for pagination)
        page: Current page number (1-indexed)
        page_size: Items per page
        total_pages: Total number of pages
    """
    activity: list[ActivityItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ModelMetricsResponse(BaseModel):
    """Aggregated vLLM model performance KPIs for admin dashboard.

    All rates are percentages (0.0–100.0). Latency values are in milliseconds.
    Fields are None when no LLM calls have occurred in the requested period.
    """
    total_analyses: int
    total_llm_calls: int
    total_errors: int
    error_rate: float
    fallback_rate: float
    avg_latency_ms: Optional[float]
    min_latency_ms: Optional[float]
    max_latency_ms: Optional[float]
    mode_llm: int
    mode_hybrid: int
    mode_rules_only: int


class TopPhrase(BaseModel):
    phrase: str
    count: int


class FrequencyTrendItem(BaseModel):
    category: str
    count: int
    top_phrases: list[TopPhrase]


class FrequencyTrendsResponse(BaseModel):
    trends: list[FrequencyTrendItem]
    days: int


# ── Rules management schemas ──────────────────────────────────────────────────

class RuleItem(BaseModel):
    rule_id: UUID
    language: str
    name: str
    description: Optional[str]
    category: str
    default_severity: str
    pattern_type: str
    pattern_value: str
    example_bad: Optional[str]
    example_good: Optional[str]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class RulesListResponse(BaseModel):
    rules: list[RuleItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class RuleCreate(BaseModel):
    language: Literal['he', 'en']
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = Field(min_length=1, max_length=100)
    default_severity: Literal['low', 'medium', 'high'] = 'medium'
    pattern_type: Literal['regex', 'keyword', 'prompt', 'other']
    pattern_value: str = Field(min_length=1)
    example_bad: Optional[str] = None
    example_good: Optional[str] = None


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    default_severity: Optional[Literal['low', 'medium', 'high']] = None
    pattern_type: Optional[Literal['regex', 'keyword', 'prompt', 'other']] = None
    pattern_value: Optional[str] = Field(default=None, min_length=1)
    example_bad: Optional[str] = None
    example_good: Optional[str] = None
    is_enabled: Optional[bool] = None
