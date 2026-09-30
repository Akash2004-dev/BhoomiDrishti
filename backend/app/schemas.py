from typing import Literal, Optional

from pydantic import BaseModel, Field


class SalvageAdvisory(BaseModel):
    immediate_action: str = Field(description="General suggested next step; requires local agronomist review")
    drainage_required: bool
    fungicide_spray_recommended: bool


class GeminiVisualAssessment(BaseModel):
    valid_agricultural_sample: bool
    identified_crop_type: str
    crop_growth_stage: str
    damage_phenotype: str
    crop_lodging_percentage: float = Field(ge=0, le=100)
    inundation_severity: str
    estimated_loss_percentage: float = Field(ge=0, le=100)
    confidence_score: float = Field(ge=0, le=1)
    audit_notes: str
    salvage_advisory: SalvageAdvisory


class SatelliteSpectralSummary(BaseModel):
    source: Literal["earth_engine", "unavailable", "simulated"]
    pre_event_ndvi: Optional[float] = None
    post_event_ndvi: Optional[float] = None
    delta_ndvi: Optional[float] = None
    spectral_loss_detected: Optional[bool] = None
    cloud_obscured: bool = False
    message: Optional[str] = None


class ClaimDossierResponse(BaseModel):
    claim_id: str
    timestamp: str
    latitude: float
    longitude: float
    crop_type: str
    damage_phenotype: str
    visual_loss_percentage: float
    satellite_source: Literal["earth_engine", "unavailable", "simulated"]
    pre_event_ndvi: Optional[float] = None
    post_event_ndvi: Optional[float] = None
    satellite_ndvi_delta: Optional[float] = None
    computed_final_loss_percentage: Optional[float] = None
    estimate_basis: str
    audit_verdict: str
    tamper_hash: str
    salvage_guidance: str
    transcribed_context: Optional[str] = None
    evidence_note: Optional[str] = None
