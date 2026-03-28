from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Aegis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/simulate")
async def simulate(
    text: str = Form(""),
    image: UploadFile | None = File(None),
):
    image_info = None
    if image and image.filename:
        contents = await image.read()
        image_info = {
            "filename": image.filename,
            "content_type": image.content_type,
            "size_bytes": len(contents),
        }

    return {
        "status": "received",
        "text_length": len(text),
        "text_preview": text[:200] if text else None,
        "image": image_info,
        "message": "Payload received. ML analysis not yet implemented.",
    }
