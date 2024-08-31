from pydantic import BaseModel
from typing import List, Optional, Dict, Union

class MedicationInfo(BaseModel):
    name: str
    dosage: str = None
    frequency: str = None

class PrescriptionData(BaseModel):
    id: Optional[int] = None
    Name: Optional[str] = None
    age: Optional[str] = None
    prescription_date: Optional[str] = None
    medication_name: List[str] = []
    medication_dosage: Dict[str, str] = {}
    prescription_days: Optional[int] = None

class DrugIngredient(BaseModel):
    성분명: str
    분량: str

class DrugInfo(BaseModel):
    품목명: str
    주성분: Dict[str, DrugIngredient]
    요약_보고서: str

class StructuredDrugInfo(DrugInfo):
    drug_id: Optional[int] = None
    patient_id: Optional[int] = None
    성상: Optional[str] = None
    효능효과: Optional[str] = None
    용법용량: Optional[str] = None
    주의사항: Optional[str] = None
    저장방법: Optional[str] = None
    유효기간: Optional[str] = None
    재심사기간: Optional[str] = None
    포장단위: Optional[str] = None
    허가종류: Optional[str] = None
    제조_수입: Optional[str] = None
    업체명: Optional[str] = None
    품목일련번호: Optional[str] = None
    허가일자: Optional[str] = None
    전문_일반: Optional[str] = None
    재심사대상: Optional[str] = None

class Patient(BaseModel):
    id: Optional[int] = None
    name: str = None
    age: Union[int, str] = None
    gender: str = None
    medications: Optional[List[str]] = None