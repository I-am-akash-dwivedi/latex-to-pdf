import os
import subprocess

from fastapi import FastAPI, File, Response, UploadFile

app = FastAPI()


@app.get("/")
def home():
    return {"status": "ok", "message": "The API is up and running"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/compile")
def compile_tex(file: UploadFile = File(...)):
    tex_file = "temp.tex"
    pdf_file = "temp.pdf"
    
    # Save uploaded file
    with open(tex_file, "wb") as f:
        f.write(file.file.read())

    try:
        # Run pdflatex
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # ✅ merge stderr into stdout
            check=True
        )

        # Read PDF
        with open(pdf_file, "rb") as f:
            pdf_bytes = f.read()

        return Response(pdf_bytes, media_type="application/pdf")

    except subprocess.CalledProcessError as e:
        return {
            "error": "LaTeX compilation failed",
            "details": e.output.decode("utf-8")
        }

    finally:
        for ext in [".aux", ".log", ".pdf", ".tex"]:
            try:
                os.remove(tex_file.replace(".tex", ext))
            except FileNotFoundError:
                pass
