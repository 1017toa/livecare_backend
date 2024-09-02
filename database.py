import json
import aiosqlite
import sqlite3
import json
from contextlib import contextmanager, asynccontextmanager
from loguru import logger

@contextmanager
def create_connection_sync():
    try:
        conn = sqlite3.connect('medical_data.db')
        yield conn
    except Exception as e:
        logger.error(f"데이터베이스 연결 오류 (동기): {e}")
        raise
    finally:
        conn.close()

@asynccontextmanager
async def create_connection_async():
    try:
        conn = await aiosqlite.connect('medical_data.db')
        logger.info("데이터베이스 연결 성공")
        yield conn
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {str(e)}")
        raise
    finally:
        try:
            await conn.close()
            logger.info("데이터베이스 연결 종료")
        except Exception as e:
            logger.error(f"데이터베이스 연결 종료 실패: {str(e)}")

async def create_tables(conn):
    try:
        await conn.executescript('''
            CREATE TABLE IF NOT EXISTS patients
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             name TEXT,
             age INTEGER,
             gender TEXT,
             medications TEXT);  -- JSON 형식의 정수 배열을 저장할 TEXT 컬럼

            CREATE TABLE IF NOT EXISTS drug_info
            (drug_id INTEGER PRIMARY KEY,
             patient_id INTEGER,
             품목명 TEXT,
             주성분 TEXT,
             요약_보고서 TEXT,
             성상 TEXT,
             효능효과 TEXT,
             용법용량 TEXT,
             주의사항 TEXT,
             저장방법 TEXT,
             유효기간 TEXT,
             재심사기간 TEXT,
             포장단위 TEXT,
             허가종류 TEXT,
             제조_수입 TEXT,
             업체명 TEXT,
             품목일련번호 TEXT,
             허가일자 TEXT,
             전문_일반 TEXT,
             재심사대상 TEXT);

            CREATE TABLE IF NOT EXISTS medical_charts
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             patient_id INTEGER,
             content TEXT);
                                 
            CREATE TABLE IF NOT EXISTS voice_medical_charts
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             patient_id INTEGER,
             content TEXT);                                 
        ''')
        await conn.commit()
        logger.info("테이블 생성 완료: patients, drug_info, medical_charts")
    except Exception as e:
        logger.error(f"테이블 생성 오류: {e}")

async def insert_prescription(conn, prescription_data, file_metadata):
    try:
        cursor = await conn.execute('''
            INSERT INTO prescriptions (
                file_hash, patient_name, patient_age, prescription_date,
                medication_name, medication_dosage, prescription_days
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            file_metadata['file_hash'],
            prescription_data.name,
            prescription_data.age,
            prescription_data.prescription_date,
            ', '.join(prescription_data.medication_name),
            json.dumps(prescription_data.medication_dosage),
            prescription_data.prescription_days
        ))
        await conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"처방전 데이터 삽입 오류: {str(e)}")
        await conn.rollback()
        raise

async def get_prescription_by_hash(conn, file_hash):
    sql = '''SELECT id, file_hash, patient_name, patient_age, prescription_date, medication_name, medication_dosage, prescription_days
             FROM prescriptions WHERE file_hash = ?'''
    try:
        async with conn.execute(sql, (file_hash,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'file_hash': row[1],
                    'patient_name': row[2],
                    'patient_age': row[3],
                    'prescription_date': row[4],
                    'medication_name': row[5].split(', '),
                    'medication_dosage': json.loads(row[6]),
                    'prescription_days': row[7]
                }
        return None
    except Exception as e:
        logger.error(f"파일 해시로 처방전 조회 오류: {e}")
        return None

def get_medical_chart_by_hash(conn, file_hash):
    sql = 'SELECT id, content FROM medical_charts WHERE file_hash = ?'
    try:
        c = conn.cursor()
        c.execute(sql, (file_hash,))
        row = c.fetchone()
        return {'id': row[0], 'content': row[1]} if row else None
    except Error as e:
        logger.error(f"의료 차트 조회 오류: {e}")
        return None

async def get_drug_info_by_name(conn, 품목명):
    sql = 'SELECT * FROM drug_info WHERE 품목명 = ?'
    try:
        async with conn.execute(sql, (품목명,)) as cursor:
            row = await cursor.fetchone()
            if row:
                주성분 = row[2]
                try:
                    주성분_parsed = json.loads(주성분) if 주성분 else []
                except json.JSONDecodeError:
                    logger.warning(f"주성분 파싱 오류: {주성분}")
                    주성분_parsed = []
                
                return {
                    'id': row[0],
                    '품목명': row[1],
                    '주성분': 주성분_parsed,
                    '요약_보고서': row[3],
                    '성상': row[4],
                    '효능효과': row[5],
                    '용법용량': row[6],
                    '주의사항': row[7],
                    '저장방법': row[8],
                    '유효기간': row[9],
                    '재심사기간': row[10],
                    '포장단위': row[11],
                    '허가종류': row[12],
                    '제조_수입': row[13],
                    '업체명': row[14],
                    '품목일련번호': row[15],
                    '허가일자': row[16],
                    '전문_일반': row[17],
                    '재심사대상': row[18]
                }
        return None
    except Exception as e:
        logger.error(f"약품 정보 조회 오류: {e}")
        return None

async def get_drug_info_by_id(conn, drug_id):
    sql = 'SELECT * FROM drug_info WHERE drug_id = ?'
    try:
        async with conn.execute(sql, (drug_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'drug_id': row[0],
                    'patient_id': row[1],
                    '품목명': row[2],
                    '주성분': json.loads(row[3]),
                    '요약_보고서': row[4],
                    '성상': row[5],
                    '효능효과': row[6],
                    '용법용량': row[7],
                    '주의사항': row[8],
                    '저장방법': row[9],
                    '유효기간': row[10],
                    '재심사기간': row[11],
                    '포장단위': row[12],
                    '허가종류': row[13],
                    '제조_수입': row[14],
                    '업체명': row[15],
                    '품목일련번호': row[16],
                    '허가일자': row[17],
                    '전문_일반': row[18],
                    '재심사대상': row[19]
                }
        return None
    except Exception as e:
        logger.error(f"약품 정보 조회 오류: {e}")
        return None

def update_medical_chart(conn, id, chart_content):
    sql = '''UPDATE medical_charts
             SET content = ?
             WHERE id = ?'''
    try:
        c = conn.cursor()
        c.execute(sql, (chart_content, id))
        conn.commit()
        if c.rowcount == 0:
            logger.warning(f"ID {id}에 해당하는 의료 차트가 없습니다.")
            return False
        logger.info(f"ID {id}의 의료 차트 내용이 성공적으로 업데이트되었습니다.")
        return True
    except Error as e:
        logger.error(f"의료 차트 내용 업데이트 오류: {e}")
        return False

def update_drug_info(conn, id, drug_info):
    sql = '''UPDATE drug_info
             SET drug_id=?, 품목명=?, 주성분=?, 요약_보고서=?, 성상=?, 효능효과=?, 용법용량=?, 주의사항=?,
                 저장방법=?, 유효기간=?, 재심사기간=?, 포장단위=?, 허가종류=?, 제조_수입=?,
                 업체명=?, 품목일련번호=?, 허가일자=?, 전문_일반=?, 재심사대상=?
             WHERE id=?'''
    try:
        c = conn.cursor()
        c.execute(sql, (
            drug_info.drug_id,
            drug_info.품목명,
            json.dumps(drug_info.주성분),
            drug_info.요약_보고서,
            drug_info.성상,
            drug_info.효능효과,
            drug_info.용법용량,
            drug_info.주의사항,
            drug_info.저장방법,
            drug_info.유효기간,
            drug_info.재심사기간,
            drug_info.포장단위,
            drug_info.허가종류,
            drug_info.제조_수입,
            drug_info.업체명,
            drug_info.품목일련번호,
            drug_info.허가일자,
            drug_info.전문_일반,
            drug_info.재심사대상,
            id
        ))
        conn.commit()
        if c.rowcount == 0:
            logger.warning(f"ID {id}에 해당하는 약품 정보가 없습니다.")
            return False
        logger.info(f"ID {id}의 약품 정보가 성공적으로 업데이트되었습니다.")
        return True
    except Error as e:
        logger.error(f"약품 정보 업데이트 오류: {e}")
        return False

async def insert_drug_info(conn, structured_data):
    sql = '''INSERT INTO drug_info (
                품목명, 성상, 주성분, 효능효과, 용법용량, 주의사항, 저장방법, 유효기간,
                재심사기간, 포장단위, 허가종류, 제조_수입, 업체명, 품목일련번호,
                허가일자, 전문_일반, 재심사대상, 요약_보고서
             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
    
    try:
        # DrugIngredient 객체를 딕셔너리로 변환
        주성분_dict = {k: v.__dict__ for k, v in structured_data.주성분.items()}
        주성분_json = json.dumps(주성분_dict)
        
        await conn.execute(sql, (
            structured_data.품목명,
            structured_data.성상,
            주성분_json,  # 주성분 정보를 JSON으로 직렬화
            structured_data.효능효과,
            structured_data.용법용량,
            structured_data.주의사항,
            structured_data.저장방법,
            structured_data.유효기간,
            structured_data.재심사기간,
            structured_data.포장단위,
            structured_data.허가종류,
            structured_data.제조_수입,
            structured_data.업체명,
            structured_data.품목일련번호,
            structured_data.허가일자,
            structured_data.전문_일반,
            structured_data.재심사대상,
            structured_data.요약_보고서
        ))
        await conn.commit()
        logger.info(f"새로운 약품 정보가 성공적으로 저장되었습니다: {structured_data.품목명}")
        return True
    except Exception as e:
        logger.error(f"약품 정보 저장 중 오류 발생: {str(e)}")
        if conn.in_transaction:
            await conn.rollback()
        return False

async def insert_patient(conn, patient):
    sql = '''INSERT INTO patients (name, age, gender, medications)
             VALUES (?, ?, ?, ?)'''
    try:
        medications_json = json.dumps(patient.medications) if patient.medications else None
        cursor = await conn.execute(sql, (patient.name, patient.age, patient.gender, medications_json))
        await conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"환자 데이터 삽입 오류: {e}")
        await conn.rollback()
        raise

async def get_patient_by_id(conn, patient_id):
    sql = '''SELECT id, name, age, gender, medications
             FROM patients WHERE id = ?'''
    try:
        async with conn.execute(sql, (patient_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'age': row[2],
                    'gender': row[3],
                    'medications': json.loads(row[4]) if row[4] else None
                }
        return None
    except Exception as e:
        logger.error(f"환자 조회 오류: {e}")
        return None

async def insert_medical_chart_from_prescription(conn, patient_id, content):
    sql = '''INSERT INTO medical_charts (patient_id, content)
             VALUES (?, ?)'''
    try:
        cursor = await conn.execute(sql, (patient_id, content))
        await conn.commit()
        logger.info(f"환자 ID {patient_id}의 의료 차트가 성공적으로 저장되었습니다.")
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"의료 차트 저장 오류: {e}")
        raise

async def insert_voice_medical_chart(conn, patient_id, content):
    sql = '''INSERT INTO voice_medical_charts (patient_id, content)
             VALUES (?, ?)'''
    try:
        cursor = await conn.execute(sql, (patient_id, content))
        await conn.commit()
        logger.info(f"환자 ID {patient_id}의 음성 진료 차트가 성공적으로 저장되었습니다.")
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"음성 진료 차트 저장 오류: {e}")
        raise