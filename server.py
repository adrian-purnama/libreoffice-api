import os
from flask import Flask, request, send_file
from werkzeug.utils import secure_filename
import subprocess

app = Flask(__name__)
UPLOAD_FOLDER = "/tmp"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route("/")
def index():
    return "LibreOffice Flask API is running."


@app.route("/convert", methods=["POST"])
def convert_file():
    if "file" not in request.files:
        return {"error": "No file part"}, 400

    file = request.files["file"]

    if file.filename == "":
        return {"error": "No file selected"}, 400

    filename = secure_filename(file.filename)
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)

    # Output will be same name but with .pdf
    output_path = input_path + ".pdf"

    # LibreOffice conversion command
    command = [
        "soffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", app.config['UPLOAD_FOLDER'],
        input_path
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        return {"error": "Conversion failed"}, 500

    # Return the converted PDF file
    return send_file(output_path, as_attachment=True, download_name="converted.pdf")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3501)
