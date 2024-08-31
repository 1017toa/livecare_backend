import os
from decorators import async_timing_decorator
from dotenv import load_dotenv
import aiohttp
import asyncio
import re
import xml.etree.ElementTree as ET
import html
from langchain_handler import LangChainHandler
from database import insert_drug_info, get_drug_info_by_name, update_drug_info
from models import StructuredDrugInfo
from loguru import logger

class DrugProductInfo:
    def __init__(self):
        load_dotenv()
        
        self.API_KEY = os.getenv('OPEN_DATA_API_KEY')
        self.BASE_URL = "http://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService06"
        self.API_ENDPOINT = "getDrugPrdtPrmsnDtlInq05"
        
        self.lang_chain_handler = LangChainHandler()
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @staticmethod
    def clean_doc_content(content):
        if not content:
            return ""
        cdata_pattern = r'<!\[CDATA\[(.*?)\]\]>'
        article_pattern = r'<ARTICLE title="([^"]*)">'
        
        cleaned_content = []
        for match in re.finditer(f'{cdata_pattern}|{article_pattern}', content, re.DOTALL):
            if match.group().startswith('<![CDATA['):
                cleaned_content.append(match.group(1).strip())
            else:
                cleaned_content.append(match.group())
        
        result = '\n'.join(cleaned_content)
        
        # Remove content between <tbody> and </tbody>
        result = re.sub(r'<tbody>.*?</tbody>', '', result, flags=re.DOTALL)
        
        return result

    async def fetch_api_data(self, item_name):
        url = f"{self.BASE_URL}/{self.API_ENDPOINT}"
        params = {
            'serviceKey': self.API_KEY,
            'pageNo': '1',
            'numOfRows': '10',
            'type': 'json',
            'item_name': item_name
        }

        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

    async def parse_drug_info(self, api_result, conn):
        drug_info = api_result[0]  # API 결과의 첫 번째 항목 사용

        logger.info(f"drug_info 주성분: {drug_info.get('MATERIAL_NAME')}")
        
        structured_data = StructuredDrugInfo(
            품목명=drug_info.get('ITEM_NAME'),
            성상=drug_info.get('CHART'),
            주성분=self.parse_main_ingredients(drug_info.get('MATERIAL_NAME')),
            효능효과=self.clean_doc_content(drug_info.get('EE_DOC_DATA')),
            용법용량=self.clean_doc_content(drug_info.get('UD_DOC_DATA')),
            주의사항=self.clean_doc_content(drug_info.get('PN_DOC_DATA')),
            저장방법=drug_info.get('STORAGE_METHOD'),
            유효기간=drug_info.get('VALID_TERM'),
            재심사기간=drug_info.get('REEXAM_DATE'),
            포장단위=drug_info.get('PACK_UNIT'),
            허가종류=drug_info.get('PERMIT_KIND_NAME'),
            제조_수입=drug_info.get('MAKE_MATERIAL_FLAG'),
            업체명=drug_info.get('ENTP_NAME'),
            품목일련번호=drug_info.get('ITEM_SEQ'),
            허가일자=drug_info.get('ITEM_PERMIT_DATE'),
            전문_일반=drug_info.get('ETC_OTC_CODE'),
            재심사대상=drug_info.get('REEXAM_TARGET'),
            요약_보고서=""  # 초기값 설정
        )

        logger.info(f"structured_data 주성분: {structured_data.주성분}")

        # 데이터베이스에 저장
        existing_drug = await get_drug_info_by_name(conn, structured_data.품목명)
        if existing_drug:
            simplified_data = existing_drug
            return simplified_data
        
        # 주요 이상반응 데이터 요약
        original_adverse_reactions = self.clean_doc_content(drug_info.get('NB_DOC_DATA'))
        summarized_adverse_reactions = await self.lang_chain_handler.summarize_drug_info(original_adverse_reactions, structured_data.dict())
        
        structured_data.요약_보고서 = summarized_adverse_reactions  # 요약된 주요 이상반응 추가
        
        if not existing_drug:
            await insert_drug_info(conn, structured_data)
            print(f"새로운 약품 정보 저장: {structured_data.품목명}")
        
        # 품목명, 주성분, 주요 이상반응만 있는 간단한 데이터 생성
        simplified_data = {
            "품목명": structured_data.품목명,
            "주성분": structured_data.주성분,
            "요약_보고서": structured_data.요약_보고서
        }
        
        return simplified_data

    @staticmethod
    def parse_main_ingredients(material_name):
        if not material_name:
            return {}
        
        ingredients = {}
        parts = material_name.split(';')
        for part in parts:
            match = re.search(r'총량 : (.+?)\|성분명 : (.+?)\|분량 : (.+?)\|단위 : (.+?)\|', part)
            if match:
                total, name, amount, unit = match.groups()
                layer = '기본'  # 기본 레이어 이름 설정
                if '중' in total:
                    layer = total.split('중')[0].strip()
                ingredients[layer] = {
                    "성분명": name,
                    "분량": f"{amount} {unit}"
                }
        return ingredients

    @async_timing_decorator
    async def get_drug_product_info(self, item_name, conn):
        data = await self.fetch_api_data(item_name)
        
        if data and 'body' in data and 'items' in data['body']:
            원본_데이터_길이 = sum(len(str(value)) for item in data['body']['items'] for value in item.values())
            print(f"구조화되기 전 데이터: {원본_데이터_길이}")
            structured_data = await self.parse_drug_info(data['body']['items'], conn)
            구조화된_데이터_길이 = sum(len(str(value)) for value in structured_data.values())
            print(f"구조화된 데이터:\n{구조화된_데이터_길이}")
            return structured_data
        else:
            print(f"API {self.API_ENDPOINT}에서 데이터를 찾을 수 없습니다.")
            return None