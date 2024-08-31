import asyncio
import os
from dotenv import load_dotenv
import aiohttp
import re
from loguru import logger

class OpenDataGrain:
    def __init__(self):
        load_dotenv()
        self.API_KEY = os.getenv('OPEN_DATA_API_KEY')

    async def get_pill_info(self, session, item_name):
        url = "http://apis.data.go.kr/1471000/MdcinGrnIdntfcInfoService01/getMdcinGrnIdntfcInfoList01"
        params = {
            'serviceKey': self.API_KEY,
            'item_name': item_name,
            'numOfRows': 30,
            'pageNo': 1,
            'type': 'json'
        }
        
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if 'body' in data and 'items' in data['body']:
                    items = data['body']['items']
                    if len(items) >= 2:
                        filtered_items = [item for item in items if item['ITEM_NAME'].startswith(item_name)]
                        if filtered_items:
                            return item_name, filtered_items
                    return item_name, data['body']['items']
                else:
                    # 아이템 이름의 마지막 부분이 숫자로 구성된 경우 제거하고 다시 검색
                    new_item_name = re.sub(r'\d+$', '', item_name)
                    if new_item_name != item_name:
                        return await self.get_pill_info(session, new_item_name)
                    else:
                        # print(f"경고: {item_name}에 대한 예상치 못한 응답 구조")
                        # print(f"응답 데이터: {data}")
                        return item_name, None
            else:
                return item_name, None

    def calculate_word_ratio(self, word, item_name):
        word_count = sum(1 for char in word if char in item_name)
        return word_count / len(item_name)

    async def search_pills_from_text(self, text):
        # 텍스트에서 단어 추출 및 중복 제거
        words = re.findall(r'\w+', text)
        unique_words = sorted(set(words))
        
        # '캅셀'과 '캡슐' 변형 단어 추가
        additional_words = []
        for word in unique_words:
            if "캅셀" in word:
                additional_words.append(word.replace("캅셀", "캡슐"))
            elif "캡슐" in word:
                additional_words.append(word.replace("캡슐", "캅셀"))
        unique_words.extend(additional_words)
        
        # 단어 길이 순으로 정렬 (긴 단어부터)
        unique_words = sorted(set(unique_words), key=len, reverse=True)
        
        # 다른 단어에 완전히 포함되는 단어 제거
        filtered_unique_words = []
        for word in unique_words:
            if not any(word != other_word and word in other_word for other_word in unique_words):
                filtered_unique_words.append(word)
        
        unique_words = filtered_unique_words
        logger.debug(f"unique_words: {unique_words}")
        
        # 비동기 세션 생성 및 약품 정보 조회
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.get_pill_info(session, word.replace("밀리그램", "").replace("mg", "").rstrip('_'))
                for word in unique_words
                if len(word) > 2 and not word.isdigit() and not word.isascii()
            ]
            results = await asyncio.gather(*tasks)
        
        # 결과 필터링: 단어로 시작하는 약품 정보만 선택
        filtered_results = {}
        for word, pill_info in results:
            if pill_info:
                filtered_info = [
                    item for item in pill_info
                    if item['ITEM_NAME'].startswith(word)
                ]
                if filtered_info:
                    filtered_results[word] = filtered_info
        
        return filtered_results

