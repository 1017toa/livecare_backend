import asyncio
import hashlib
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import Any, List, Dict, Union, Optional
import requests
import json
from langchain_handler import LangChainHandler
from langchain_teddynote import logging
from dotenv import load_dotenv
import os
from loguru import logger
import sys
import time
from functools import wraps, partial
import aiohttp
import time
from database import (
    create_tables,
    insert_drug_info,
    insert_medical_chart,
    get_medical_chart_by_hash,
    get_medical_chart_by_id,
    insert_medical_chart_from_prescription,
    update_medical_chart, create_connection_async,
    create_connection_sync
)
from open_data_grain import OpenDataGrain
from prescription_handler import PrescriptionHandler
from models import PrescriptionData
from decorators import async_timing_decorator
from ocr import document_ocr  # 이 import 문을 파일 상단에 추가해주세요
from s3 import upload_file_to_s3

from contextlib import asynccontextmanager
from PIL import Image
import io
import math
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 실행
    logger.info("애플리케이션 시작: DB 테이블 생성")
    async with create_connection_async() as conn:
        await create_tables(conn)
        logger.info("DB 테이블 생성 완료")
    
    yield
    
    # 종료 시 실행 (필요한 경우)
    logger.info("애플리케이션 종료")

app = FastAPI(lifespan=lifespan)

# Load environment variables
load_dotenv()

# 프로젝트 이름을 입력합니다.
logging.langsmith("livecare")

# CORS 설정
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 'logs' 디렉토리 확인 및 생성
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    logger.info(f"'{log_dir}' 디렉토리가 생성되었습니다.")

# 로거 설정
logger.remove()  # 기본 핸들러 제거
logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
logger.add(f"{log_dir}/app.log", rotation="500 MB", retention="10 days", level="DEBUG")

def calculate_file_hash(file_binary):
    return hashlib.md5(file_binary).hexdigest()

langchain_handler = LangChainHandler()
prescription_handler = PrescriptionHandler()


@app.post("/extract_prescription", response_model=Any)
@async_timing_decorator
async def extract_prescription(file: UploadFile = File(...)):
    logger.info(f"처방전 추출 시작: 파일명 {file.filename}")
    
    async def process_ocr_result(ocr_result):
        async with create_connection_async() as conn:
            patient_result = await prescription_handler.process_new_prescription(ocr_result, conn)
            logger.debug(f"환자 데이터 추출 완료: {patient_result}")
            detailed_info = await prescription_handler.get_detailed_drug_info(patient_result, conn)
            logger.debug(f"상세 약품 정보 추출 완료: {detailed_info}")
            return patient_result, detailed_info

    async with aiohttp.ClientSession() as session:
        file_content = await file.read()
        
        # 현재 시간을 문자열로 추가하여 고유한 파일 이름 생성
        timestamp = int(time.time())
        unique_filename = f"{timestamp}.pdf"
        
        # S3에 파일 업로드 (비동기적으로 실행하고 결과를 기다리지 않음)
        asyncio.create_task(upload_file_to_s3(file_content, unique_filename))
        
        ocr_result = await document_ocr(file_content)
        logger.debug(f"OCR 처리 완료")
        logger.debug(f"OCR 텍스트 길이: {len(ocr_result.get('text', ''))}")
        
        patient_result, detailed_info = await process_ocr_result(ocr_result)
        
        # create_multidisciplinary_care 함수를 통해 결과 처리
        final_result = await langchain_handler.create_multidisciplinary_care(patient_result, detailed_info)

        # final_result를 medical_charts 테이블에 저장
        async with create_connection_async() as conn:
            chart_id = await insert_medical_chart_from_prescription(conn, patient_result.id, final_result)
            logger.info(f"의료 차트 저장 완료: 차트 ID {chart_id}")

    logger.info(f"처방전 추출 및 저장 성공")
    return {"result": final_result, "chart_id": chart_id}

@app.post("/transcribe_audio")
@async_timing_decorator
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    logger.info(f"음성 파일 전사 시작: 파일명 {file.filename}")
    try:
        file_content = await file.read()
        file_hash = calculate_file_hash(file_content)
        
        # 데이터베이스 연결
        conn = create_connection()
        if conn is not None:
            create_tables(conn)
            
            # 해시로 기존 의료 차트 검색
            existing_chart = get_medical_chart_by_hash(conn, file_hash)
            if existing_chart:
                logger.info("중복된 파일이 감지되어 기존 결과를 반환합니다.")
                conn.close()
                return {"id": existing_chart['id'], "content": existing_chart['content']}
        
        # 새로운 파일인 경우 처리 계속
        temp_file_path = f"tmp/{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file_content)
        transcribe_result = transcribe_audio(temp_file_path)
        logger.info(f"음성 파일 전사 성공: {file.filename}")
        final_result = await langchain_handler.create_medical_chart(transcribe_result['text'])
        logger.info(f"의료 차트 생성 성공: {file.filename}")
        
        file_metadata = {
            'file_name': file.filename,
            'file_size': len(file_content),
            'file_type': file.content_type,
            'file_hash': file_hash
        }
        
        # 데이터베이스에 저장
        if conn is not None:
            chart_id = insert_medical_chart(conn, final_result, file_metadata)
            conn.close()
            if chart_id:
                final_result = {"id": chart_id, "content": final_result}
            else:
                logger.error("의료 차트 저장 실패")
        
        return final_result

    except Exception as e:
        logger.error(f"음성 파일 전사 중 오류 발생: {str(e)}")
        raise

@app.put("/update_prescription/{prescription_id}")
@async_timing_decorator
async def update_prescription_endpoint(prescription_id: int, prescription: PrescriptionData):
    logger.info(f"처방전 업데이트 시작: ID {prescription_id}")
    try:
        conn = create_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="데이터베이스 연결 실패")
        
        create_tables(conn)
        
        # 기존 처방전 검색
        existing_prescription = get_prescription_by_id(conn, prescription_id)
        if not existing_prescription:
            conn.close()
            raise HTTPException(status_code=404, detail="해당 처방전을 찾을 수 없습니다")
        
        # 처방전 업데이트
        success = update_prescription(conn, prescription_id, prescription)
        conn.close()
        
        if success:
            logger.info(f"처방전 업데이트 성공: ID {prescription_id}")
            return {"message": "처방전이 성공적으로 업데이트되었습니다."}
        else:
            raise HTTPException(status_code=500, detail="처방전 업데이트 실패")
    except HTTPException as he:
        logger.error(f"처방전 업데이트 중 HTTP 오류 발생: {str(he)}")
        raise
    except Exception as e:
        logger.error(f"처방전 업데이트 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class MedicalChartUpdate(BaseModel):
    id: int
    content: str

@app.put("/update_medical_chart/{chart_id}")
@async_timing_decorator
async def update_medical_chart_endpoint(chart_id: int, medical_chart: MedicalChartUpdate):
    logger.info(f"의료 차트 업데이트 시작: 차트 ID {chart_id}")
    try:
        conn = create_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="데이터베이스 연결 실패")
        
        create_tables(conn)
        
        # 기존 의료 차트 검색
        existing_chart = get_medical_chart_by_id(conn, chart_id)
        if not existing_chart:
            conn.close()
            raise HTTPException(status_code=404, detail="해당 의료 차트를 찾을 수 없습니다")
        
        # 요청된 차트 ID와 페이로드의 ID가 일치하는지 확인
        if chart_id != medical_chart.id:
            conn.close()
            raise HTTPException(status_code=400, detail="요청 URL의 차트 ID와 페이로드의 ID가 일치하지 않습니다")
        
        # 의료 차트 업데이트
        success = update_medical_chart(conn, chart_id, medical_chart.content)
        conn.close()
        
        if success:
            logger.info(f"의료 차트 업데이트 성공: 차트 ID {chart_id}")
            return {"message": "의료 차트가 성공적으로 업데이트되었습니다."}
        else:
            raise HTTPException(status_code=500, detail="의료 차트 업데이트 실패")
    except HTTPException as he:
        logger.error(f"의료 차트 업데이트 중 HTTP 오류 발생: {str(he)}")
        raise
    except Exception as e:
        logger.error(f"의료 차트 업데이트 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("애플리케이션 시작")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)