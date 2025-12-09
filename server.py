import os
import uuid
import subprocess
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

API_PASSWORD = os.getenv("API_PASSWORD")  # Optional security


@app.route("/")
def index():
    return "LibreOffice Flask API is running."


def allowed_ext(filename):
    ALLOWED = ["pdf", "doc", "docx"]
    ext = filename.lower().split(".")[-1]
    return ext if ext in ALLOWED else None


@app.route("/convert", methods=["POST"])
def convert_file():
    # ------ AUTH ------
    password = request.headers.get("X-API-KEY")
    if API_PASSWORD and password != API_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    # ------ VALIDATE FILE ------
    if "file" not in request.files:
        return jsonify({"error": "No file found"}), 400

    input_file = request.files["file"]
    original_name = secure_filename(input_file.filename)

    ext = allowed_ext(original_name)
    if ext is None:
        return jsonify({"error": "Unsupported file type"}), 400

    # Save temp file
    file_id = str(uuid.uuid4())
    input_path = f"/tmp/{file_id}_{original_name}"
    input_file.save(input_path)

    # ------ OUTPUT TYPE ------
    output_format = request.args.get("to", "pdf").lower()

    # ------ OPTIONAL MARGINS ------
    # margins in mm → convert to twips
    def mm_to_twips(mm):
        return int(float(mm) * 56.7)

    margins = {}

    if "margin_top" in request.args:
        margins["MargTop"] = mm_to_twips(request.args["margin_top"])

    if "margin_bottom" in request.args:
        margins["MargBottom"] = mm_to_twips(request.args["margin_bottom"])

    if "margin_left" in request.args:
        margins["MargLeft"] = mm_to_twips(request.args["margin_left"])

    if "margin_right" in request.args:
        margins["MargRight"] = mm_to_twips(request.args["margin_right"])

    filter_options = ""
    if margins:
        import json
        filter_options = json.dumps(margins)

    # ------ BUILD COMMAND ------
    command = [
        "soffice",
        "--headless",
        "--convert-to", f"pdf:writer_pdf_Export",
        "--outdir", "/tmp"
    ]

    if filter_options:
        command.append(f'--writer-filter-options={filter_options}')

    command.append(input_path)

    # ------ RUN LO ------
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "Conversion failed", "details": str(e)}), 500

    # Output path
    out_base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = f"/tmp/{out_base}.pdf"

    # ------ SEND BACK ------
    response = send_file(output_path, as_attachment=True, download_name=f"converted.pdf")

    try:
        os.remove(input_path)
        os.remove(output_path)
    except:
        pass

    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3501)
