import os
from dotenv import load_dotenv
import aiohttp
import asyncio

# 환경 변수 로드
load_dotenv()

# API 키 가져오기
API_KEY = os.getenv('OPEN_DATA_API_KEY')

# 기본 URL 설정
BASE_URL = "http://apis.data.go.kr/1471000/DURPrdlstInfoService03"

# API 엔드포인트 목록과 설명
API_ENDPOINTS = {
    "getUsjntTabooInfoList03": "병용금기 정보조회",
    "getOdsnAtentInfoList03": "노인주의 정보조회",
    "getDurPrdlstInfoList03": "DUR품목정보 조회",
    "getSpcifyAgrdeTabooInfoList03": "특정연령대금기 정보조회",
    "getCpctyAtentInfoList03": "용량주의 정보조회",
    "getMdctnPdAtentInfoList03": "투여기간주의 정보조회",
    "getEfcyDplctInfoList03": "효능군중복 정보조회",
    "getSeobangjeongPartitnAtentInfoList03": "서방정분할주의 정보조회",
    "getPwnmTabooInfoList03": "임부금기 정보조회"
}

async def fetch_api_data(session, endpoint, item_name):
    url = f"{BASE_URL}/{endpoint}"
    params = {
        'serviceKey': API_KEY,
        'itemName': item_name,
        'pageNo': '1',
        'numOfRows': '10',
        'type': 'json'
    }

    async with session.get(url, params=params) as response:
        if response.status == 200:
            data = await response.json()
            return endpoint, data
        else:
            return endpoint, None

async def get_drug_info(item_name):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_api_data(session, endpoint, item_name) for endpoint in API_ENDPOINTS]
        results = await asyncio.gather(*tasks)
    
    drug_info = {}
    for endpoint, data in results:
        if data and 'body' in data and 'items' in data['body']:
            drug_info[endpoint] = data['body']['items']
        else:
            drug_info[endpoint] = None
    
    return drug_info

# 사용 예시
async def main():
    item_name = "본에콕스"
    drug_info = await get_drug_info(item_name)
    
    for endpoint, info in drug_info.items():
        print(f"API: {endpoint}")
        print(f"설명: {API_ENDPOINTS[endpoint]}")
        if info:
            print(f"결과: {info}")
        else:
            print("결과 없음")
        print("---")

if __name__ == "__main__":
    asyncio.run(main())