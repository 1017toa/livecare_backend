from fastapi import HTTPException
from pydantic import BaseModel
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv
from google.oauth2 import id_token
from google.auth.transport import requests

# 환경 변수 로드
load_dotenv()

# 환경 변수에서 설정 값 가져오기
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

class Token(BaseModel):
    access_token: str
    token_type: str

class UserAuth(BaseModel):
    id_token: str

def verify_google_token(token: str):
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('잘못된 발급자입니다.')
        return idinfo
    except ValueError:
        raise HTTPException(status_code=401, detail="유효하지 않은 Google 토큰")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_info(decoded_token: dict):
    return {
        "uid": decoded_token["sub"],
        "email": decoded_token.get("email"),
        "name": decoded_token.get("name"),
        "picture": decoded_token.get("picture")
    }

# JWT 토큰 검증 함수 (선택적)
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰")