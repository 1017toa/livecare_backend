import aiohttp
import os
from dotenv import load_dotenv
from decorators import async_timing_decorator

# Load environment variables
load_dotenv()

@async_timing_decorator
async def document_ocr(file_contents):
    async with aiohttp.ClientSession() as session:
        api_key = os.getenv("UPSTAGE_API_KEY")
        url = "https://api.upstage.ai/v1/document-ai/ocr"
        headers = {"Authorization": f"Bearer {api_key}"}
        data = aiohttp.FormData()
        data.add_field('document', file_contents)
        async with session.post(url, headers=headers, data=data) as response:
            response_json = await response.json()
    return response_json