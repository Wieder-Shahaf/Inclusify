# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel
# import httpx

# router = APIRouter()

# # 1. Define the input model (what receives from Frontend)
# class AnalysisRequest(BaseModel):
#     text: str

# # 2. Define the System Prompt for the AI
# SYSTEM_PROMPT = """
# You are an inclusive language expert assistant.
# Analyze the provided text for non-inclusive language (gender bias, ableism, etc.).
# If issues are found, suggest corrections.
# Return the answer in a clear JSON structure with: "original_text", "issues_found" (list), and "suggestion".
# """

# @router.post("/analyze")
# async def analyze_text(request: AnalysisRequest):
#     """
#     Receives text and sends it to Azure AI (Llama-3) for analysis.
#     """
    
#     # --- HERE ARE YOUR KEYS (We need to fill them from Azure Portal) ---
#     azure_endpoint = "YOUR_AZURE_ENDPOINT_URL"  # e.g., https://inclusify-project.openai.azure.com/
#     api_key = "YOUR_AZURE_API_KEY"
#     deployment_name = "llama-3-70b" # Or whatever you named your deployment
    
#     # If keys are missing, stop here
#     if "YOUR_" in azure_endpoint:
#         raise HTTPException(status_code=500, detail="Azure keys are missing in the code!")

#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {api_key}", # For some Azure models it is "api-key": api_key
#     }

#     payload = {
#         "messages": [
#             {"role": "system", "content": SYSTEM_PROMPT},
#             {"role": "user", "content": request.text}
#         ],
#         "temperature": 0.7,
#         "max_tokens": 800
#     }

#     # Call Azure AI
#     try:
#         async with httpx.AsyncClient() as client:
#             # Construct the full URL for chat completions
#             url = f"{azure_endpoint}/v1/chat/completions" 
            
#             response = await client.post(url, json=payload, headers=headers, timeout=60.0)
            
#             if response.status_code != 200:
#                 raise HTTPException(status_code=response.status_code, detail=f"Azure Error: {response.text}")
            
#             result = response.json()
#             # Extract the actual text answer
#             ai_message = result["choices"][0]["message"]["content"]
            
#             return {"analysis": ai_message}

#     except Exception as e:
#         print(f"Error calling AI: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))
from fastapi import APIRouter
from pydantic import BaseModel
import asyncio

router = APIRouter()

class AnalysisRequest(BaseModel):
    text: str

@router.post("/analyze")
async def analyze_text(request: AnalysisRequest):
    """
    DEMO MODE: Simulates AI analysis for the meeting.
    """
    # אנחנו עושים השהייה קטנה של שנייה וחצי כדי שזה ירגיש כאילו ה-AI חושב
    await asyncio.sleep(1.5)
    
    # זו התשובה שהמערכת תחזיר תמיד (כאילו ניתחה את הטקסט)
    fake_ai_response = {
        "original_text": request.text,
        "analysis_status": "Success",
        "issues_found": [
            {
                "type": "Gender Bias",
                "severity": "Medium",
                "description": "השימוש במילה 'רופאים' בלשון זכר עלול להיות לא מכליל.",
                "suggestion": "מומלץ להשתמש ב'צוות רפואי' או 'רופאות ורופאים'."
            }
        ],
        "corrected_text": "צוות רפואי טיפל בחולים במסירות.",
        "note": "This is a DEMO response generated locally (Waiting for Azure keys)."
    }
    
    return fake_ai_response