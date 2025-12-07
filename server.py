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
    # ------------- AUTH CHECK (optional) ------------------
    password = request.headers.get("X-API-KEY")
    if API_PASSWORD and password != API_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    # ------------- VALIDATE INPUT FILE --------------------
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    input_file = request.files["file"]

    if input_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Detect extension
    original_name = secure_filename(input_file.filename)
    ext = allowed_ext(original_name)

    if ext is None:
        return jsonify({"error": "Unsupported file type"}), 400

    # Temporary unique filename to avoid conflicts
    file_id = str(uuid.uuid4())
    input_path = f"/tmp/{file_id}_{original_name}"
    input_file.save(input_path)

    # ------------- DETECT OUTPUT TYPE ---------------------
    output_format = request.args.get("to", "pdf").lower()

    if output_format not in ["pdf", "doc", "docx"]:
        return jsonify({"error": "Unsupported output format"}), 400

    # LibreOffice output
    output_dir = "/tmp"
    command = [
        "soffice",
        "--headless",
        "--convert-to",
        output_format,
        "--outdir",
        output_dir,
        input_path
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "LibreOffice conversion failed", "details": str(e)}), 500

    # Output filename (LibreOffice replaces extension automatically)
    output_path = f"/tmp/{os.path.splitext(os.path.basename(input_path))[0]}.{output_format}"

    # ------------- SEND BACK FILE -------------------------
    response = send_file(output_path, as_attachment=True, download_name=f"converted.{output_format}")

    # ------------- CLEANUP TEMP FILES ---------------------
    try:
        os.remove(input_path)
        os.remove(output_path)
    except Exception:
        pass  # Non-fatal cleanup issue

    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3501)
