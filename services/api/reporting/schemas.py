"""Pydantic schemas for reporting APIs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WeeklyLocationPerformanceOut(BaseModel):
    id: UUID
    location_id: int
    country: str
    week_start: date
    total_purchase_cost: float
    total_waste_cost: float
    waste_ratio: float
    stockout_events_count: int
    price_alert_events_count: int
    currency: str
    computed_at: datetime

    model_config = {"from_attributes": True}


class PipelineRunOut(BaseModel):
    id: UUID
    flow_name: str
    week_start: Optional[date] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    records_extracted: int = 0
    records_loaded: int = 0
    records_processed: int = 0
    records_skipped_missing_cost: int = 0
    status: str
    errors: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class PipelineRunAccepted(BaseModel):
    status: str = "accepted"
    message: str = Field(
        default="Weekly location performance pipeline started in the background"
    )
