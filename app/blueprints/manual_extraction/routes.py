import os

import bleach
from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from datetime import datetime
from decimal import Decimal

from consultation_emails.extract.text_handler import PlaintextHolder
from consultation_emails.logger.logger import logger
from consultation_emails.schemas.dynamo_db import QuestionSchema, ResponseIdSchema, ManualIdSchema

manual_extraction_bp = Blueprint("manual_extraction", __name__, template_folder="templates")


# Route to show highlighted extracted text
@manual_extraction_bp.route("/manual_extraction/<string:response_id>", methods=["GET"])
def review_highlighted_text(response_id: str):
    """
    Route to show highlighted extracted text.
    Args:
        response_id (str): The ID of the response being reviewed.
    Returns:
        werkzeug.wrappers.Response: A response rendering the highlighted text page.
    """
    logger.info(f"Redirecting to highlighted text for response id: {response_id}...")

    response_ids = list(session.get("response_question_ids").keys())
    response_ids_names = {item["id"]: item["pdf_path"] for item in session.get("model_outputs")}

    questions_schema = current_app.dynamo_db_handler.query_partition_key(
        key=response_id, key_name="response_id", table_name=os.environ["QUESTIONS_TABLE_NAME"]
    )
    validated_questions_schema = [QuestionSchema(**question) for question in questions_schema]

    # only get the most recent questions - otherwise the app will highlight historical data
    max_question_timestamp = max(validated_question_schema.timestamp for validated_question_schema in validated_questions_schema)
    validated_questions_schema = [
        validated_question_schema
        for validated_question_schema in validated_questions_schema
        if validated_question_schema.timestamp == max_question_timestamp
    ]

    response_schema = current_app.dynamo_db_handler.query_partition_key(
        key=response_id, key_name="response_id", table_name=os.environ["RESPONSES_TABLE_NAME"]
    )[0]

    validated_response_schema = ResponseIdSchema(**response_schema)
    full_response_text = validated_response_schema.plain_text

    # Rendering plaintext
    # For security sanitise html fragments before processing (except <mark> tags will be added later)
    full_response_text = bleach.clean(full_response_text, strip=False)
    plaintext_holder = PlaintextHolder(full_response_text)

    search_results = []
    for validated_question_schema in validated_questions_schema:
        for search_string in validated_question_schema.exact_extracted_text:
            search_string = bleach.clean(search_string, strip=False)
            search_results.extend(plaintext_holder.exact_text_search(search_string, max_results=None))

    # Adding <mark> tags to the search results
    full_response_text = plaintext_holder.mark_text(search_results, reverse=False)

    return render_template(
        "manual_extraction.html",
        highlighted_text=full_response_text,
        response_id=response_id,
        response_ids=response_ids,
        current_page="manual_extraction",
        questions=session["local_questions"],
        manual_extractions=session.get("manual_extractions", {}).get(response_id, {}),
        response_ids_names=response_ids_names,
    )


@manual_extraction_bp.route("/manual_extraction/submit", methods=["POST"])
def submit_extraction():
    """
    Handles the submission or clearing of extracted text for a specific question.

    This route processes form data submitted by the user to represent
    manually extracted text for a specific question associated with a response.
    Input is saved in the session and also uploaded to DynamoDB.

    Steps:
    1. Extracts form data including response ID, question label, extracted text, and start time.
    2. Validates the presence of required fields and handles missing or invalid data.
    3. Retrieves the latest manual extraction record from DynamoDB for the given response and question.
    4. Updates the session and DynamoDB with the new or cleared extracted text.
    5. Redirects the user back to the highlighted text review page.

    Returns:
        werkzeug.wrappers.Response: A redirect response to the highlighted text review page.
    """
    logger.info("submit_extraction route called, extracting form data...")
    # Extract form data
    response_id = request.form.get("response_id")
    if not response_id:
        logger.error("Response ID not found in form data.")
        logger.error("Form data: %s", request.form)
        return redirect(url_for("manual_extraction.review_highlighted_text"))
    question_label = request.form.get("question_label")
    extracted_text = request.form.get("extracted_text", "")
    start_time = request.form.get("start_time")

    if not start_time:
        logger.warning(f"Invalid or missing start_time for response {response_id}, question {question_label}. Defaulting to current timestamp.")
        start_time = str(int(datetime.now().timestamp()))
    else:
        logger.info(f"start_time successfully retrieved: {start_time}")

    # Fetch the latest record from DynamoDB
    logger.info("Retrieving most recent Manual extraction data...")

    entry_manual = current_app.dynamo_db_handler.query_partition_key_sort_key(
        table_name=os.environ["MANUAL_TABLE_NAME"],
        partition_key="response_id",
        partition_value=response_id,
        sort_key="question_label",
        sort_value=question_label,
    )
    existing_record = entry_manual[0] if entry_manual else {}

    logger.info("Successfully retrieved most recent Manual extraction data.")
    logger.info("Validating Manual extraction data...")

    validated_entry_manual = ManualIdSchema(**existing_record)

    logger.info("Successfully validated Manual extraction data.")

    if "manual_extractions" not in session:
        session["manual_extractions"] = {}
    if response_id not in session["manual_extractions"]:
        session["manual_extractions"][response_id] = {}

    session["manual_extractions"][response_id][question_label] = extracted_text
    session.modified = True  # Ensure session changes are saved

    # Update the validated entry with the new user input
    logger.info("Updating Manual extraction data...")
    validated_entry_manual.manual_text = extracted_text
    validated_entry_manual.timestamp = [Decimal(str(start_time)), Decimal(str(int(datetime.now().timestamp())))]
    validated_entry_manual.status = "Modified"

    # Save the updated entry back to DynamoDB
    logger.info(f"Uploading Manual extraction data for response {response_id}, question {question_label}...")
    current_app.dynamo_db_handler.upload_data(data=validated_entry_manual.model_dump(), table_name=os.environ["MANUAL_TABLE_NAME"])
    logger.info(f"Updated Manual Extraction for response {response_id}, question {question_label}")

    logger.info(f"Submission saved for response {response_id}, question_label: {question_label}")
    return redirect(url_for("manual_extraction.review_highlighted_text", response_id=response_id))
