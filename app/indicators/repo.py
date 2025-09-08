#  all repos classes related to indicators

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class IndicatorBase(BaseModel):
    """
    Define a base class for indicators with various properties.
    @param BaseModel - The base model class
    @field indicator_name - The name of the indicator
    @field category - The category of the indicator
    @field description - The description of the indicator
    @field formula - The formula used by the indicator
    @field dependencies - The dependencies required by the indicator
    @field parameters - The parameters used by the indicator
    @field_validator dependencies_must_be_object - Validates that dependencies are in JSON object format
    """
    indicator_name: str = Field(..., min_length=1)
    category: Optional[str] = None
    description: Optional[str] = None
    formula: str = Field(..., min_length=1)
    dependencies: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('dependencies')
    def dependencies_must_be_object(cls, v):
        if not isinstance(v, dict):
            raise ValueError('dependencies must be a JSON object')
        return v


class IndicatorCreate(IndicatorBase):
    """
    Create a new indicator class that inherits from the IndicatorBase class.
    This class does not have any additional methods or attributes beyond what is inherited from IndicatorBase.
    """
    pass


class IndicatorUpdate(BaseModel):
    """
    Define a class for updating indicators based on a base model.
    @param BaseModel - The base model for the indicator update.
    @attribute indicator_name - The name of the indicator.
    @attribute category - The category of the indicator.
    @attribute description - The description of the indicator.
    @attribute formula - The formula used for the indicator.
    @attribute dependencies - The dependencies of the indicator.
    @attribute parameters - The parameters used for the indicator.
    """
    indicator_name: Optional[str]
    category: Optional[str]
    description: Optional[str]
    formula: Optional[str]
    dependencies: Optional[Dict[str, Any]]
    parameters: Optional[Dict[str, Any]]


class IndicatorOut(IndicatorBase):
    """
    Define a class `IndicatorOut` that inherits from `IndicatorBase` and includes the following attributes:
    - id: str
    - created_at: Optional[str]
    - updated_at: Optional[str]
    """
    id: str
    created_at: Optional[str]
    updated_at: Optional[str]