import os
from dotenv import load_dotenv
import aiohttp
import asyncio
import re
import xml.etree.ElementTree as ET
import html

content = """
<DOC title=\"용법용량\" type=\"UD\">\r\n  <SECTION title=\"\">\r\n    <ARTICLE title=\"\">\r\n      <PARAGRAPH tagName=\"p\" textIndent=\"\" marginLeft=\"\"><![CDATA[성인 : 1일 2회, 1회 1정 복용한다.]]></PARAGRAPH>\r\n      <PARAGRAPH tagName=\"p\" textIndent=\"\" marginLeft=\"\"><![CDATA[이 약은 식사와 관계없이 투여할 수 있다.]]></PARAGRAPH>\r\n      <PARAGRAPH tagName=\"p\" textIndent=\"\" marginLeft=\"\"><![CDATA[이 약은 분쇄하거나 분할하지 않고 전체를 복용한다.]]></PARAGRAPH>\r\n      <PARAGRAPH tagName=\"p\" textIndent=\"\" marginLeft=\"\"><![CDATA[○ 간장애 환자]]></PARAGRAPH>\r\n      <PARAGRAPH tagName=\"p\" textIndent=\"\" marginLeft=\"\"><![CDATA[투여 용량 감량이 필요한 간장애 환자 초기 치료 시, 이 약의 투여는 권장되지 않는다 (사용상의 주의사항 중 5. 일반적 주의)]]></PARAGRAPH>\r\n    </ARTICLE>\r\n  </SECTION>\r\n</DOC>"
"""

def clean_content_for_PN_DOC_DATA(content):
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

cleaned_content = clean_content_for_PN_DOC_DATA(content)
print(cleaned_content)
print(f"before length: {len(content)}")
print(f"after length: {len(cleaned_content)}")