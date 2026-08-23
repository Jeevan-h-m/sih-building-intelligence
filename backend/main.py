from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, HTTPException, UploadFile
from cv.wall_detection import detect_walls
from cv.preprocessing import preprocess_blueprint
from fastapi.staticfiles import StaticFiles
app = FastAPI(title="SIH Building Intelligence API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
UPLOAD_DIR = Path("data/uploads")
PROCESSED_DIR = Path("data/processed")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/blueprints/processed",
    StaticFiles(directory=str(PROCESSED_DIR)),
    name="processed-blueprints",
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "SIH Building Intelligence backend is running",
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
            detail="Only PNG, JPEG, and PDF files are supported.",
        )

    file_path = UPLOAD_DIR / file.filename

    contents = await file.read()
    file_path.write_bytes(contents)

    return {
        "message": "Blueprint uploaded successfully",
        "filename": file.filename,
        "path": str(file_path),
    }


@app.post("/blueprints/process")
async def process_blueprint(file: UploadFile = File(...)):
    allowed_types = {
        "image/png",
        "image/jpeg",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="For preprocessing, upload a PNG or JPEG blueprint.",
        )

    input_path = UPLOAD_DIR / file.filename
    output_path = PROCESSED_DIR / f"{input_path.stem}_processed.png"

    contents = await file.read()
    input_path.write_bytes(contents)

    try:
        preprocess_blueprint(
            str(input_path),
            str(output_path),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return {
    "message": "Blueprint processed successfully",
    "original_filename": file.filename,
    "processed_filename": output_path.name,
    "processed_url": f"/blueprints/processed/{output_path.name}",
}
@app.post("/blueprints/detect-walls")
async def detect_blueprint_walls(file: UploadFile = File(...)):
    allowed_types = {
        "image/png",
        "image/jpeg",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Wall detection currently supports PNG and JPEG.",
        )

    input_path = UPLOAD_DIR / file.filename
    output_path = PROCESSED_DIR / f"{input_path.stem}_walls.png"

    contents = await file.read()
    input_path.write_bytes(contents)

    try:
        walls = detect_walls(
            str(input_path),
            str(output_path),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return {
    "message": "Wall detection completed",
    "filename": output_path.name,
    "wall_detection_url": (
        f"/blueprints/processed/{output_path.name}"
    ),
    "wall_count": len(walls),
    "walls": walls,
}