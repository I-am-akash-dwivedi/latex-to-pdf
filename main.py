import asyncio
import os
import subprocess
import uuid

import aiofiles
from fastapi import BackgroundTasks, FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI()


@app.get("/")
def home():
    return {"status": "ok", "message": "The API is up and running"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/compile")
async def compile_tex(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    tex_filename = f"{uuid.uuid4()}.tex"
    pdf_filename = tex_filename.replace(".tex", ".pdf")
    
    # Save uploaded file
    async with aiofiles.open(tex_filename, "wb") as f:
        await f.write(await file.read())

    try:
        # Run pdflatex
        process = await asyncio.create_subprocess_exec(
            "pdflatex", "-interaction=nonstopmode", tex_filename,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await process.communicate()
        
        if process.returncode != 0:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "LaTeX compilation failed",
                    "details": stdout.decode("utf-8")
                }
            )
            
        background_tasks.add_task(os.remove, pdf_filename)  # delete after response
        return FileResponse(
            path=pdf_filename,
            media_type="application/pdf",
            filename="resume.pdf"
        )


    except subprocess.CalledProcessError as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": "An error occured. LaTeX compilation failed",
                "details": e.output.decode("utf-8"),
                "stderr": e.stderr.decode()
            }
        )

    finally:
        # Cleanup everything except the PDF, since FileResponse still needs it
        for ext in [".aux", ".log", ".tex"]:
            try:
                os.remove(tex_filename.replace(".tex", ext))
            except FileNotFoundError:
                pass
