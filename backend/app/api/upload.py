from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import io
from PyPDF2 import PdfReader
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
from app.services.invite_service import require_invite_session
import base64
import json

router = APIRouter(dependencies=[Depends(require_invite_session)])

@router.post("/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    """
    업로드된 PDF 파일에서 텍스트를 추출하여 반환합니다.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")
        
    try:
        content = await file.read()
        pdf_reader = PdfReader(io.BytesIO(content))
        
        extracted_text = ""
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
                
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="PDF에서 텍스트를 추출할 수 없습니다. 이미지 기반 PDF일 수 있습니다.")
            
        return {"text": extracted_text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류가 발생했습니다: {str(e)}")

class JDAnalysisRequest(BaseModel):
    text: str | None = None
    image: str | None = None  # Base64

@router.post("/analyze-jd")
async def analyze_jd(request: JDAnalysisRequest):
    """
    채용 공고(텍스트 또는 이미지)를 분석하여 지원 직무(Job Title)를 추출합니다.
    """
    try:
        # GPT-5.4-nano 모델 사용 (요청에 따름)
        llm = ChatOpenAI(
            model="gpt-5.4-nano", 
            openai_api_key=settings.OPENAI_API_KEY,
            max_completion_tokens=500 # 최신 모델 대응
        )
        
        content = []
        if request.text:
            content.append({"type": "text", "text": f"다음 채용 공고 내용에서 가장 핵심적인 '지원 직무명(Job Title)' 하나만 짧게 추출해줘. 다른 설명 없이 직무명만 답변해.\n\n공고 내용:\n{request.text}"})
        
        if request.image:
            # base64 이미지 데이터 (data:image/jpeg;base64,... 형태 대응)
            image_url = request.image
            if not image_url.startswith("data:image"):
                image_url = f"data:image/jpeg;base64,{image_url}"
                
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })
            if not request.text:
                content.append({"type": "text", "text": "위 이미지(채용 공고)에서 가장 핵심적인 '지원 직무명(Job Title)' 하나만 짧게 추출해줘. 다른 설명 없이 직무명만 답변해."})

        if not content:
            raise HTTPException(status_code=400, detail="분석할 내용(텍스트 또는 이미지)이 없습니다.")

        response = llm.invoke([HumanMessage(content=content)])
        job_title = response.content.strip().replace("직무명:", "").replace("직무:", "").strip()
        
        # 따옴표 제거 등 정제
        if job_title.startswith("'") or job_title.startswith('"'):
            job_title = job_title[1:-1]
            
        return {"job_title": job_title}
        
    except Exception as e:
        print(f"JD Analysis Error: {str(e)}")
        # 에러 발생 시 빈값 반환하여 프론트에서 수동 입력 유도
        return {"job_title": ""}
