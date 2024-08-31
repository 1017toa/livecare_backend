import asyncio
import logging
from typing import Dict, Any, List, Tuple
from database import get_prescription_by_hash, insert_prescription, insert_patient, get_patient_by_id
from decorators import async_timing_decorator
from models import PrescriptionData, MedicationInfo, Patient
from ocr import document_ocr
from open_data_grain import OpenDataGrain
from langchain_handler import LangChainHandler
from drug_product_info import DrugProductInfo
from loguru import logger

class PrescriptionHandler:
    def __init__(self):
        self.open_data_grain = OpenDataGrain()
        self.langchain_handler = LangChainHandler()
        self.drug_product_info = DrugProductInfo()

    async def check_existing_prescription(self, file_hash: str, conn) -> PrescriptionData | None:
        existing_prescription = get_prescription_by_hash(conn, file_hash)
        if existing_prescription:
            logger.info("중복된 파일이 감지되어 기존 결과를 반환합니다.")
            return PrescriptionData(**existing_prescription)
        return None

    @async_timing_decorator
    async def process_new_prescription(self, ocr_result: Dict[str, Any], conn) -> Patient:
        logger.info("처방전 처리 시작")
        
        text = ocr_result.get('text', '')
        logger.info(f"추출된 텍스트 길이: {len(text)} 문자")

        logger.info("알약 이름 검색 시작")
        item_names = await self.get_pill_item_names(text)
        logger.info(f"알약 이름 검색 완료: {item_names}")
        
        logger.info("메타데이터 추출 시작")
        metadata = await self.langchain_handler.extract_metadata(text, item_names, temperature=0.0)
        logger.info(f"메타데이터 추출 완료: {metadata}")
        
        # 환자 정보 추출 및 저장
        patient_data = Patient(**metadata)
        if item_names:
            patient_data.medications = item_names
        patient_id = await insert_patient(conn, patient_data)
        if patient_id:
            patient_data.id = patient_id
        
        logger.info("처방전 처리 완료")

        return patient_data

    async def get_pill_item_names(self, text: str) -> list:
        pill_results = await self.open_data_grain.search_pills_from_text(text)
        item_names = []
        for items in pill_results.values():
            if isinstance(items, list) and len(items) > 0 and isinstance(items[0], dict) and 'ITEM_NAME' in items[0]:
                item_names.append(items[0]['ITEM_NAME'])
        logger.debug(f"알약 검색 결과: {len(item_names)} 개 항목 발견")
        return item_names
    
    async def get_detailed_drug_info(self, metadata_result: Patient, conn) -> List[Dict[str, Any]]:
        async with self.drug_product_info:
            tasks = [self.drug_product_info.get_drug_product_info(item_name, conn) 
                     for item_name in metadata_result.medications]
            results = await asyncio.gather(*tasks)
        
        detailed_info = []
        for item_name, drug_info in zip(metadata_result.medications, results):
            if drug_info:
                detailed_info.append(drug_info)
            else:
                logger.warning(f"약품 정보를 찾을 수 없음: {item_name}")
        
        logger.debug(f"상세 약품 정보: {len(detailed_info)} 개 항목 검색 완료")
        return detailed_info

    async def save_prescription(self, conn, result: PrescriptionData, file_metadata: Dict[str, Any]) -> PrescriptionData:
        prescription_id = await insert_prescription(conn, result, file_metadata)
        if prescription_id:
            result.id = prescription_id
        else:
            logger.error("처방전 저장 실패")
        return result
    async def process_files(self, files, conn):
        tasks = [self.process_new_prescription(file, conn) for file in files]
        results = await asyncio.gather(*tasks)
        return results

