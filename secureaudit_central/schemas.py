from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocalScanInput(StrictModel):
    """An empty request; no command or user-controlled script path is accepted."""
    pass


class EndpointInput(StrictModel):
    hostname: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    group_name: str = Field(default="Unassigned", max_length=100)
    platform: str = Field(default="Windows", max_length=100)


class CheckEvidence(StrictModel):
    check_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=200)
    status: Literal["Pass", "Fail", "Error"]
    detail: str = Field(max_length=10000)
    severity: Literal["Low", "Medium", "High", "Critical"] = "Medium"
    scanner_result: dict | None = None

    @model_validator(mode="after")
    def consistent_scanner_result(self):
        if self.scanner_result is not None:
            if self.scanner_result.get("check_id") != self.check_id or self.scanner_result.get("status") != self.status:
                raise ValueError("Scanner result must match check_id and status")
        return self


class EvidenceInput(StrictModel):
    submission_id: str = Field(min_length=1, max_length=100)
    collected_at: datetime
    checks: list[CheckEvidence] = Field(min_length=1, max_length=100)

    @field_validator("collected_at")
    @classmethod
    def aware_timestamp(cls, value):
        if value.tzinfo is None:
            raise ValueError("collected_at must include a timezone")
        if value.timestamp() > datetime.now(timezone.utc).timestamp() + 300:
            raise ValueError("collected_at cannot be in the future")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def unique_checks(self):
        if len({c.check_id for c in self.checks}) != len(self.checks):
            raise ValueError("Duplicate check IDs are not allowed")
        return self


class DemoSeed(StrictModel):
    count: int = Field(default=100, ge=1, le=500)


class JobInput(StrictModel):
    endpoint_ids: list[str] = Field(min_length=1, max_length=500)
    delay_seconds: int = Field(default=0, ge=0, le=86400)

    @model_validator(mode="after")
    def unique_endpoints(self):
        if len(set(self.endpoint_ids)) != len(self.endpoint_ids):
            raise ValueError("Duplicate endpoint IDs are not allowed")
        return self
