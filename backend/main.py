from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from engine import analyze_threat

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
    image_bytes = None
    if image and image.filename:
        image_bytes = await image.read()

    result = analyze_threat(draft_text=text, image_bytes=image_bytes)
    return result
