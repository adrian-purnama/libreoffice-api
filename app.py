from flask import Flask, request, send_file
import subprocess, os, uuid

app = Flask(__name__)

@app.post("/convert")
def convert():
    # Get uploaded file
    if "file" not in request.files:
        return {"error": "file is required"}, 400

    file = request.files["file"]

    # Default output format
    output_format = request.form.get("format", "doc")

    # Temporary paths
    uid = str(uuid.uuid4())
    input_path = f"/tmp/{uid}.docx"
    output_path = f"/tmp/{uid}.{output_format}"

    # Save the file
    file.save(input_path)

    # Convert using LibreOffice
    subprocess.run([
        "libreoffice", "--headless",
        "--convert-to", output_format,
        "--outdir", "/tmp", input_path
    ], check=True)

    # Return converted file
    return send_file(output_path, as_attachment=True)

@app.get("/")
def health():
    return {"status": "running"}
