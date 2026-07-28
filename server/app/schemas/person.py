from pydantic import BaseModel
from typing import Optional


class PersonCreate(BaseModel):
    full_name: str

    person_type: Optional[str] = None

    department: Optional[str] = None

    position: Optional[str] = None

    subjects: Optional[str] = None

    phone: Optional[str] = None

    email: Optional[str] = None

    office: Optional[str] = None

    notes: Optional[str] = None