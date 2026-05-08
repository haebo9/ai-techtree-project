from fastapi import APIRouter, UploadFile, File, HTTPException
import io
from PyPDF2 import PdfReader

router = APIRouter()

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
