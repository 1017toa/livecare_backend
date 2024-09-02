import requests
import json
from dotenv import load_dotenv
import os
from loguru import logger

# 환경 변수 로드
load_dotenv()

class ClovaSpeechClient:
    def __init__(self):
        self.invoke_url = os.getenv('CLOVA_SPEECH_INVOKE_URL')
        self.secret = os.getenv('CLOVA_SPEECH_SECRET_KEY')

    def req_upload(self, file, completion, callback=None, userdata=None, forbiddens=None, boostings=None,
                   wordAlignment=True, fullText=True, diarization={'enable': False}, sed=None):
        request_body = {
            'language': 'ko-KR',
            'completion': completion,
            'callback': callback,
            'userdata': userdata,
            'wordAlignment': wordAlignment,
            'fullText': fullText,
            'forbiddens': forbiddens,
            'boostings': boostings,
            'diarization': diarization,
            'sed': sed,
        }
        headers = {
            'Accept': 'application/json;UTF-8',
            'X-CLOVASPEECH-API-KEY': self.secret
        }
        files = {
            'media': open(file, 'rb'),
            'params': (None, json.dumps(request_body, ensure_ascii=False).encode('UTF-8'), 'application/json')
        }
        try:
            response = requests.post(headers=headers, url=self.invoke_url + '/recognizer/upload', files=files)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Clova Speech API 요청 중 오류 발생: {str(e)}")
            raise

def transcribe_audio(file_contents):
    client = ClovaSpeechClient()
    try:
        result = client.req_upload(file_contents, completion='sync')
        logger.info(f"Clova Speech API 요청 성공: {result}")
        return result
    except Exception as e:
        logger.error(f"음성 파일 전사 중 오류 발생: {str(e)}")
        raise