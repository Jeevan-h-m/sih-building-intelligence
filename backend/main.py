from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path

app = FastAPI(title="SIH Building Intelligence API")

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "SIH Building Intelligence backend is running"
    }


@app.post("/blueprints/upload")
async def upload_blueprint(file: UploadFile = File(...)):
    allowed_types = {
        "image/png",
        "image/jpeg",
        "application/pdf",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only PNG, JPEG, and PDF files are supported."
        )

    file_path = UPLOAD_DIR / file.filename

    contents = await file.read()
    file_path.write_bytes(contents)

    return {
        "message": "Blueprint uploaded successfully",
        "filename": file.filename,
        "path": str(file_path)
    }