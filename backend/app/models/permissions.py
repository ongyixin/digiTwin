from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Role(BaseModel):
    id: str
    name: str
    description: Optional[str] = None


class Permission(BaseModel):
    id: str
    action: str  # view, edit, execute, approve, delegate
    conditions: Optional[str] = None


class Resource(BaseModel):
    id: str
    resource_type: str
    resource_ref: Optional[str] = None


class Scope(BaseModel):
    id: str
    name: str
    boundary: Optional[str] = None


class Delegation(BaseModel):
    id: str
    delegator_id: str
    delegatee_id: str
    scope_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    constraints: Optional[str] = None
