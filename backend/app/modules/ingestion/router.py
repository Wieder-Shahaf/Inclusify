from fastapi import APIRouter, UploadFile, File, HTTPException
import fitz  # PyMuPDF library for PDF processing

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Endpoint to upload a file and extract its text content.
    Currently supports: PDF.
    """
    # 1. Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Currently only PDF is supported.")
    
    try:
        # 2. Read the file bytes into memory
        file_content = await file.read()
        
        # 3. Open the PDF from memory using PyMuPDF
        doc = fitz.open(stream=file_content, filetype="pdf")
        
        extracted_text = ""
        
        # 4. Iterate over pages and extract text
        for page in doc:
            extracted_text += page.get_text() + "\n"
            
        # 5. Return the result (giving a preview of the text)
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "page_count": len(doc),
            "text_preview": extracted_text[:500] + "...",  # Show first 500 characters
            "full_text_length": len(extracted_text)
        }

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process document")