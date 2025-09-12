import asyncio
import os
import subprocess
import uuid

import aiofiles
from fastapi import BackgroundTasks, Body, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"status": "ok", "message": "The API is up and running"}

@app.get("/health")
def health():
    return {"status": "ok"}


# Utility: Compile LaTeX
async def compile_latex(tex_content: str, background_tasks: BackgroundTasks):
    tex_filename = f"{uuid.uuid4()}.tex"
    pdf_filename = tex_filename.replace(".tex", ".pdf")

    # Save .tex content
    async with aiofiles.open(tex_filename, "w", encoding="utf-8") as f:
        await f.write(tex_content)

    # Run pdflatex
    process = await asyncio.create_subprocess_exec(
        "pdflatex", "-interaction=nonstopmode", tex_filename,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    stdout, _ = await process.communicate()

    if process.returncode != 0:
        # Cleanup failed run
        for ext in [".aux", ".log", ".tex"]:
            try:
                os.remove(tex_filename.replace(".tex", ext))
            except FileNotFoundError:
                pass

        return None, stdout.decode("utf-8")

    # Cleanup aux/log/tex later
    for ext in [".aux", ".log", ".tex"]:
        try:
            background_tasks.add_task(os.remove, tex_filename.replace(".tex", ext))
        except FileNotFoundError:
            pass

    # Delete PDF after response
    background_tasks.add_task(os.remove, pdf_filename)

    return pdf_filename, None


@app.post("/compile")
async def compile_tex(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    tex_content = (await file.read()).decode("utf-8")
    pdf_filename, error = await compile_latex(tex_content, background_tasks)

    if error:
        return JSONResponse(status_code=400, content={"error": "LaTeX compilation failed", "details": error})

    if pdf_filename:
        return FileResponse(
            path=pdf_filename,
            media_type="application/pdf",
            filename="resume.pdf"
        )
    else:
        return JSONResponse(status_code=500, content={"error": "An unexpected error occurred"})
    

@app.post("/compile-text")
async def compile_from_text(background_tasks: BackgroundTasks, tex: str = Body(..., embed=True)):
    pdf_filename, error = await compile_latex(tex, background_tasks)

    if error:
        return JSONResponse(status_code=400, content={"error": "LaTeX compilation failed", "details": error})

    if pdf_filename:
        return FileResponse(
            path=pdf_filename,
            media_type="application/pdf",
            filename="resume.pdf"
        )
    else:
        return JSONResponse(status_code=500, content={"error": "An unexpected error occurred"})
