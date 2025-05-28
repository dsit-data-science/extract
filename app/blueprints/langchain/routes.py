# load_dotenv function from the dotenv module to load in environment variables from .env file
# fine for development but needs changing for production
import asyncio  # noqa: F401
import os
import time

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

from consultation_emails.logger.logger import logger

load_dotenv()


langchain_bp = Blueprint("langchain", __name__, template_folder="templates")


@langchain_bp.route("/activate_langchain", methods=["GET", "POST"])
async def activate_langchain():
    if "csv_validated" not in session:
        flash("Please upload the CSV file first")
        return redirect(url_for("upload.upload_csv"))
    if "pdf_uploaded" not in session:
        flash("Please upload the PDF files first")
        return redirect(url_for("upload.upload_pdf"))

    if request.method == "POST" and "s3_csv_path" in session and "s3_doc_paths" in session:
        csv_path = session["s3_csv_path"]
        doc_paths = session["s3_doc_paths"]

        system_key = os.environ["SYSTEM_PROMPT_TEMPLATE_PATH"]
        system_version_id = os.environ.get("SYSTEM_PROMPT_TEMPLATE_VERSION")
        human_key = os.environ["HUMAN_PROMPT_TEMPLATE_PATH"]
        human_version_id = os.environ.get("HUMAN_PROMPT_TEMPLATE_VERSION")

        system_prompt_template = current_app.storage_handler.load_jinja(key=system_key, version_id=system_version_id)
        human_prompt_template = current_app.storage_handler.load_jinja(key=human_key, version_id=human_version_id)

        session["response_question_ids"] = {}

        # run all PDFs in parallel
        async def process_pdf(doc_path):
            start_time = time.time()
            doc_text = current_app.extractor.load_document_text(doc_path)
            doc_id = current_app.response_uploader.create_doc_id(doc_text)
            session["response_question_ids"][doc_id] = []
            try:
                output = await asyncio.to_thread(
                    current_app.extractor.extract_responses, doc_path, csv_path, system_prompt_template, human_prompt_template
                )
                prompt_template = [system_key, system_version_id, human_key, human_version_id]

                # upload response schema
                response_schema = current_app.response_uploader.create_response_schema(
                    responses=output,
                    doc_id=doc_id,
                    plain_text=doc_text,
                    prompt_template=prompt_template,
                )
                current_app.dynamo_db_handler.upload_data(data=response_schema.model_dump(), table_name=os.environ["RESPONSES_TABLE_NAME"])

                # upload question data
                for question_answers in output.question_answers:
                    session["response_question_ids"][doc_id].append(question_answers.question_label)

                    logger.info(f"Creating and uploading questions data for {doc_id} and question_label {question_answers.question_label}")
                    question_data = current_app.response_uploader.create_question_schema(question_answers, doc_id)
                    current_app.dynamo_db_handler.upload_data(data=question_data.model_dump(), table_name=os.environ["QUESTIONS_TABLE_NAME"])

                    logger.info(f"Creating and uploading review data for {doc_id} and question_label {question_answers.question_label}")
                    review_data = current_app.response_uploader.create_review_schema(question_answers, doc_id)
                    current_app.dynamo_db_handler.upload_data(data=review_data.model_dump(), table_name=os.environ["REVIEW_TABLE_NAME"])

                    logger.info(f"Creating and uploading manual data for {doc_id} and question_label {question_answers.question_label}")
                    manual_data = current_app.response_uploader.create_manual_schema(question_answers, doc_id)
                    current_app.dynamo_db_handler.upload_data(data=manual_data.model_dump(), table_name=os.environ["MANUAL_TABLE_NAME"])

                end_time = time.time()
                elapsed_time = end_time - start_time
                logger.info(f"Time taken to process {doc_path}: {elapsed_time:.2f} seconds")
                return {"id": doc_id, "pdf_path": doc_path, "status": "Extraction successful"}
            except Exception as e:
                return {"id": doc_id, "pdf_path": doc_path, "status": f"Extraction failed: {e}"}

        total_start_time = time.time()
        session["model_outputs"] = await asyncio.gather(*(process_pdf(d) for d in doc_paths))
        total_end_time = time.time()
        total_elapsed_time = total_end_time - total_start_time
        logger.info(f"Time taken to process all docs: {total_elapsed_time:.2f} seconds")
        output_message = [f"{o['pdf_path']}: {o['status']}" for o in session["model_outputs"]]
        return render_template("activate_langchain.html", outputs=output_message, current_page="activate_langchain")

    return render_template("activate_langchain.html", outputs=None, current_page="activate_langchain")
