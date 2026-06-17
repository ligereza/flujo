from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

class InstagramInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str = ""
    type: str = ""
    shortcode: str = ""
    media_guess: str = ""
    download_status: str = "pending"
    manual_download_possible: bool = True
    media_type: str = ""
    file_count: int = 0
    owner: str = ""
    date_utc: str = ""

class ExtractedInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_name: str = ""
    producer: str = ""
    producer_suggested: str = ""
    venue: str = ""
    event_date: str = ""
    needs_manual_review: bool = True
    caption_from_ig: str = ""

class Manifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    tool: str = "flyer_eventos"
    name: str = ""
    created_at: str = ""
    status: str = "created"
    source: dict[str, Any] = Field(default_factory=dict)
    instagram: InstagramInfo = Field(default_factory=InstagramInfo)
    extracted_info: ExtractedInfo = Field(default_factory=ExtractedInfo)
    notes: list[str] = Field(default_factory=list)
