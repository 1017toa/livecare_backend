import boto3
import os
from dotenv import load_dotenv
from decorators import async_timing_decorator
from botocore.exceptions import ClientError
from loguru import logger

# Load environment variables
load_dotenv()

service_name = 's3'
endpoint_url = 'https://kr.object.ncloudstorage.com'
region_name = 'kr-standard'
access_key = os.getenv('NAVER_ACCESS_KEY')
secret_key = os.getenv('NAVER_SECRET_KEY')

s3 = boto3.client(service_name, endpoint_url=endpoint_url, aws_access_key_id=access_key,
                  aws_secret_access_key=secret_key)

bucket_name = 'livecare'

@async_timing_decorator
async def upload_file_to_s3(file_content, file_name):
    try:
        s3.put_object(Bucket=bucket_name, Key=file_name, Body=file_content)
        file_url = f"https://{bucket_name}.kr.object.ncloudstorage.com/{file_name}"
        logger.info(f"파일 업로드 성공: {file_url}")
        return file_url
    except ClientError as e:
        logger.error(f"S3 업로드 실패: {e}")
        return None

# ... 기존의 다른 함수들 ...