from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.schema import StrOutputParser
from langchain_upstage import ChatUpstage
from langchain_openai import ChatOpenAI
from loguru import logger

class LangChainHandler:
    def __init__(self):
        self.upstage_model = ChatUpstage(model="solar-1-mini-chat")
        self.gpt4o_mini_model = ChatOpenAI(model="gpt-4o-mini")
        self.gpt4o_model = ChatOpenAI(model="gpt-4o")

    async def extract_metadata(self, text, pill_info, temperature=0.0):
        base_prompt = self.load_prompt("extract_metadata_0.0.6")
        prompt = ChatPromptTemplate.from_template(base_prompt)
        chain = prompt | self.gpt4o_mini_model | JsonOutputParser()
        response = await chain.ainvoke({"text": text})
        return response

    async def create_medical_chart(self, text, temperature=0.0):
        logger.info("의료 차트 생성 시작")
        base_prompt = self.load_prompt("create_medical_chart_0.0.0")
        prompt = ChatPromptTemplate.from_template(base_prompt)
        chain = prompt | self.gpt4o_mini_model | StrOutputParser()
        response = await chain.ainvoke({"CONVERSATION_TRANSCRIPT": text})
        logger.info(f"response_create_medical_chart: {response}")
        return response

    async def summarize_drug_info(self, drug_info, reference_data, temperature=0.0):
        logger.info("약물 정보 요약 시작")
        base_prompt = self.load_prompt("summarize_drug_info_0.0.6")
        prompt = ChatPromptTemplate.from_template(base_prompt)
        chain = prompt | self.gpt4o_mini_model | StrOutputParser()
        response = await chain.ainvoke({"DOCUMENT": drug_info, "REFERENCE_DATA": reference_data})
        logger.info(f"response_summarize_drug_info: {response}")
        return response

    async def create_multidisciplinary_care(self, patient_info, drug_info, temperature=0.0):
        logger.info("다학제 진료 계획 생성 시작")
        base_prompt = self.load_prompt("create_multidisciplinary_care_0.1.3")
        prompt = ChatPromptTemplate.from_template(base_prompt)
        chain = prompt | self.gpt4o_mini_model | StrOutputParser()
        response = await chain.ainvoke({"PATIENT_INFO": patient_info, "DRUG_INFO": drug_info})
        logger.info(f"response_create_multidisciplinary_care: {response}")
        return response

    def load_prompt(self, file_name):
        root_path = "prompts/"
        full_path = root_path + file_name + ".xml"
        try:
            with open(full_path, 'r', encoding='utf-8') as file:
                data = file.read()
            return data
        except Exception as e:
            logger.error(f"프롬프트 로딩 중 오류 발생: {str(e)}")
            raise