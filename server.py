import os
import uuid
import subprocess
import base64
import json
from PIL import Image
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

API_PASSWORD = os.getenv("API_PASSWORD")  # Optional security


@app.route("/")
def index():
    return "LibreOffice Flask API is running, This App is created by Adrian, a part of AMFPHUB"


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


@app.route("/pdf-images", methods=["POST"])
def pdf_to_images():
    """
    Convert PDF pages to images or extract embedded images from PDF.
    
    This endpoint supports two modes:
    1. 'pages' mode: Converts each PDF page to an image (PNG or JPEG)
    2. 'extract' mode: Extracts embedded images from within the PDF
    
    Authentication:
        - Requires X-API-KEY header if API_PASSWORD is set
    
    Request Parameters:
        - file (multipart/form-data): PDF file to process
        - mode (query param): 'pages' or 'extract' (default: 'pages')
        - format (query param): 'png' or 'jpeg' (for pages mode, default: 'png')
        - dpi (query param): DPI for page conversion (default: 150, only for pages mode)
    
    Response Format:
        {
            "images": [
                {
                    "index": 0,
                    "data": "base64_encoded_image_data",
                    "format": "png",
                    "width": 1920,
                    "height": 1080
                }
            ],
            "count": 1
        }
    
    Returns:
        JSON response with base64-encoded images and metadata
    """
    # ------ AUTHENTICATION ------
    password = request.headers.get("X-API-KEY")
    if API_PASSWORD and password != API_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    
    # ------ VALIDATE FILE ------
    if "file" not in request.files:
        return jsonify({"error": "No file found"}), 400
    
    input_file = request.files["file"]
    original_name = secure_filename(input_file.filename)
    
    # Validate that file is a PDF
    ext = original_name.lower().split(".")[-1]
    if ext != "pdf":
        return jsonify({"error": "File must be a PDF"}), 400
    
    # ------ GET PARAMETERS ------
    mode = request.args.get("mode", "pages").lower()
    image_format = request.args.get("format", "png").lower()
    dpi = int(request.args.get("dpi", 150))
    
    # Validate mode parameter
    if mode not in ["pages", "extract"]:
        return jsonify({"error": "Mode must be 'pages' or 'extract'"}), 400
    
    # Validate format parameter (only for pages mode)
    if mode == "pages" and image_format not in ["png", "jpeg"]:
        return jsonify({"error": "Format must be 'png' or 'jpeg'"}), 400
    
    # Save temporary PDF file
    file_id = str(uuid.uuid4())
    input_path = f"/tmp/{file_id}_{original_name}"
    input_file.save(input_path)
    
    images_result = []
    temp_files_to_cleanup = [input_path]
    
    try:
        if mode == "pages":
            # ------ MODE 1: CONVERT PDF PAGES TO IMAGES ------
            # Use PyMuPDF to render each PDF page as a single image
            # This ensures one image per page, not extracting embedded images
            
            try:
                # Open PDF with PyMuPDF
                pdf_document = fitz.open(input_path)
                
                # Calculate zoom factor from DPI (default 150 DPI)
                # PyMuPDF uses 72 DPI as base, so zoom = desired_dpi / 72
                zoom = dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                
                # Process each page
                for page_index in range(len(pdf_document)):
                    page = pdf_document[page_index]
                    
                    # Render page to pixmap (image)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Convert pixmap to PIL Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Convert to requested format and encode to base64
                    from io import BytesIO
                    buffer = BytesIO()
                    
                    if image_format == "jpeg":
                        # JPEG doesn't support transparency, ensure RGB mode
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        img.save(buffer, format="JPEG", quality=95)
                    else:  # png
                        img.save(buffer, format="PNG")
                    
                    image_bytes = buffer.getvalue()
                    base64_data = base64.b64encode(image_bytes).decode("utf-8")
                    
                    # Add to results
                    images_result.append({
                        "index": page_index,
                        "data": base64_data,
                        "format": image_format,
                        "width": pix.width,
                        "height": pix.height
                    })
                
                pdf_document.close()
                
                if not images_result:
                    return jsonify({"error": "No pages found in PDF"}), 500
            
            except Exception as e:
                return jsonify({"error": "Failed to convert PDF pages to images", "details": str(e)}), 500
        
        else:  # mode == "extract"
            # ------ MODE 2: EXTRACT EMBEDDED IMAGES FROM PDF ------
            # Use PyMuPDF to extract images embedded within the PDF
            
            try:
                # Open PDF with PyMuPDF
                pdf_document = fitz.open(input_path)
                
                image_index = 0
                
                # Iterate through all pages
                for page_num in range(len(pdf_document)):
                    page = pdf_document[page_num]
                    
                    # Get list of images on this page
                    image_list = page.get_images(full=True)
                    
                    for img_index, img in enumerate(image_list):
                        # Get image data
                        xref = img[0]  # XREF number
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]  # Original extension (png, jpeg, etc.)
                        
                        # Get image dimensions
                        width = base_image["width"]
                        height = base_image["height"]
                        
                        # Convert to requested format if needed (for pages mode compatibility)
                        # For extract mode, we preserve original format but can convert if requested
                        if image_format in ["png", "jpeg"] and image_ext != image_format:
                            # Convert image format using PIL
                            from io import BytesIO
                            img_pil = Image.open(BytesIO(image_bytes))
                            
                            # Convert to requested format
                            output_buffer = BytesIO()
                            if image_format == "jpeg":
                                # JPEG doesn't support transparency, convert RGBA to RGB
                                if img_pil.mode == "RGBA":
                                    rgb_img = Image.new("RGB", img_pil.size, (255, 255, 255))
                                    rgb_img.paste(img_pil, mask=img_pil.split()[3])
                                    img_pil = rgb_img
                                img_pil.save(output_buffer, format="JPEG", quality=95)
                            else:
                                img_pil.save(output_buffer, format="PNG")
                            
                            image_bytes = output_buffer.getvalue()
                            final_format = image_format
                        else:
                            final_format = image_ext if image_ext else "png"
                        
                        # Encode to base64
                        base64_data = base64.b64encode(image_bytes).decode("utf-8")
                        
                        # Add to results
                        images_result.append({
                            "index": image_index,
                            "data": base64_data,
                            "format": final_format,
                            "width": width,
                            "height": height,
                            "page": page_num  # Include page number for reference
                        })
                        
                        image_index += 1
                
                pdf_document.close()
                
                if not images_result:
                    return jsonify({"error": "No embedded images found in PDF"}), 404
            
            except Exception as e:
                return jsonify({"error": "Failed to extract images from PDF", "details": str(e)}), 500
        
        # ------ RETURN RESULTS ------
        return jsonify({
            "images": images_result,
            "count": len(images_result)
        })
    
    finally:
        # ------ CLEANUP TEMPORARY FILES ------
        # Ensure all temporary files are removed
        for temp_file in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass  # Ignore cleanup errors


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3501)
