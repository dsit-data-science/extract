import csv
import io

from blueprints.upload.helper import csv_to_html
from blueprints.utils import html_format_error_string
from dotenv import load_dotenv
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from pydantic import ValidationError
from werkzeug.utils import secure_filename

from consultation_emails import logger
from consultation_emails.extract.input_csv_validation import _process_csv

load_dotenv()


upload_bp = Blueprint("upload", __name__, template_folder="templates")


@upload_bp.route("/", methods=["GET", "POST"])
def index():
    """
    The route for the index page of the Flask application.
    This is the page that appears when first loading the app.
    The user can then go to the Upload CSV page to start uploading data.
    The layout of the page is defined in the index.html file.
    """
    if request.method == "POST":
        return redirect(url_for("upload.upload_csv"))
    if request.method == "GET":
        return render_template("index.html", current_page="index")    

@upload_bp.route("/upload_csv", methods=["GET", "POST"])
def upload_csv():
    """
    The route for the upload_csv page of the Flask application.
    This page allows the user to upload their survey questions CSV file.
    The CSV file is saved within S3 and locally and displayed on the webpage in a table.
    Only CSV files are allowed to be uploaded.
    The layout of the page is defined in the upload_csv.html file.
    """

    if request.method == "GET" and "csv_path" not in session:
        logger.info("csv_path not found in session, rendering upload_csv.html")
        return render_template("upload_csv.html", current_page="upload_csv")

    if request.method == "POST":  # noqa: SIM102
        if "csv_file" in request.files:
            file = request.files["csv_file"]
            if file.filename.endswith(".csv"):
                tables = None

                try:
                    # read and decode uploaded csv
                    file.stream.seek(0)
                    file_content = file.read().decode("utf-8")
                    session["csv_validated"] = True

                    # validate csv
                    stream = io.StringIO(file_content)
                    validated_csv = _process_csv(stream)

                    # save csv to S3
                    sub_folder = "user_upload_data/"
                    csv_file = secure_filename(file.filename).replace(" ", "_")
                    session["s3_csv_path"] = sub_folder + csv_file
                    file.stream.seek(0)
                    current_app.storage_handler.upload_data(key=session["s3_csv_path"], file_obj=file)

                    # convert to HTML table for display
                    stream.seek(0)
                    reader = csv.DictReader(stream)
                    tables = [csv_to_html(reader)]
                    
                    session["local_question_labels"] = [row.question_label for row in validated_csv]
                    session["local_questions"] = [
                        {"question_label": row.question_label, "question_text": row.question_text} for row in validated_csv
                    ]
                    return render_template("upload_csv.html", tables=tables, current_page="upload_csv")

                except (ValidationError, ValueError) as e:  # ValueErrors are returned from the validate_csv function
                    error = html_format_error_string(
                        "Invalid CSV file format. Please ensure the CSV file is in the correct format", e, join="\n\n"
                    )
                    session["csv_validated"] = False
                    logger.warning("Invalid CSV file format error: %s", e)
                    return render_template("upload_csv.html", tables=tables, error=error, current_page="upload_csv")

                except Exception as e:
                    error = f"An error occurred: {e}"
                    session["csv_validated"] = False
                    logger.warning("Error when loading CSV: %s", e)
                    return render_template("upload_csv.html", tables=tables, error=e, current_page="upload_csv")
            else:
                if len(file.filename) == 0:
                    logger.info("Attempted upload without a file selected")
                    error = "No file selected"
                else:
                    logger.info("Attempted upload without .csv extension: %s", file.filename)
                    error = f"{file.filename} is not a CSV file with a .csv extension"

                if "csv_path" in session:
                    tables = [csv_to_html(session["csv_path"])]
                    return render_template("upload_csv.html", error=error, tables=tables, current_page="upload_csv")
                else:
                    return render_template("upload_csv.html", error=error, current_page="upload_csv")
        else:
            logger.error("POST to /upload_csv but csv_file not found in request.files")
            error = "Please choose a CSV file to upload."
            if "csv_path" in session:
                tables = [csv_to_html(session["csv_path"])]
                return render_template("upload_csv.html", error=error, tables=tables, current_page="upload_csv")
            else:
                return render_template("upload_csv.html", error=error, current_page="upload_csv")


@upload_bp.route("/upload_pdf", methods=["GET", "POST"])
def upload_pdf():
    """
    The route for the upload_pdf page of the Flask application.
    This page allows the user to upload their survey response pdf file(s).
    Function requires the database name to be given and the CSV file uploaded before the user can upload the pdf.
    The pdf file is saved within the Azure Blob Storage and locally, and the file name is displayed on the webpage.
    Only pdf files are allowed to be uploaded.
    The layout of the page is defined in the upload_pdf.html file.
    """
    if not session.get("csv_validated"):
        if "csv_validated" not in session:
            flash("Please upload the CSV file first")
            logger.info('"csv_validated" not found in session, redirecting to upload.upload_csv')
            return redirect(url_for("upload.upload_csv"))
        if not session["csv_validated"]:
            flash("Please upload a valid CSV file")
            logger.info("Invalid CSV file uploaded, redirecting to upload.upload_csv")
            return redirect(url_for("upload.upload_csv"))

    error = None
    uploaded_files = []
    if request.method == "POST":  # noqa: SIM102
        if "pdf_files" in request.files:
            files = request.files.getlist("pdf_files")
            if not all(file.filename.endswith((".pdf",".doc",".docx")) for file in files):
                logger.info("Attempted upload of non-PDF/DOC/DOCX file(s)")
                error = "All files must be documents ending in .pdf, .doc or .docx"
                return render_template("upload_pdf.html", error=error, uploaded_files=uploaded_files, current_page="upload_pdf")
            for file in files:
                try:
                    sub_folder = "user_upload_data/"
                    doc_file = secure_filename(file.filename).replace(" ", "_")
                    s3_doc_path = sub_folder + doc_file

                    file.stream.seek(0)
                    current_app.storage_handler.upload_data(key=s3_doc_path, file_obj=file)
                    logger.info(f"Uploaded PDF file to {s3_doc_path}")
                
                    
                    # Append uploaded files into the "uploaded_files" list
                    uploaded_files.append(s3_doc_path)
                except Exception as e:
                    logger.error("Error during file upload: %s", e)
                    error = html_format_error_string(f"An error occurred while uploading {file.filename}", e)
                    return render_template("upload_pdf.html", error=error, uploaded_files=uploaded_files, current_page="upload_pdf")
            session["pdf_uploaded"] = True
            session["s3_doc_paths"] = uploaded_files  # Store the list of PDF paths in the session
        else:
            logger.warning("POST to /upload_pdf but pdf_files not found in request.files")
            error = "Please select PDF files to upload"
            return render_template("upload_pdf.html", error=error, uploaded_files=uploaded_files, current_page="upload_pdf")
    return render_template("upload_pdf.html", error=error, uploaded_files=uploaded_files, current_page="upload_pdf")
