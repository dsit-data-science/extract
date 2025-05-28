import os
from datetime import datetime
from decimal import Decimal

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

from consultation_emails.extract.text_handler import PlaintextHolder
from consultation_emails.logger.logger import logger
from consultation_emails.schemas.dynamo_db import QuestionSchema, ResponseIdSchema, ReviewIdSchema

review_bp = Blueprint("review", __name__, template_folder="templates")


@review_bp.route("/review/<string:response_id>/<string:question_label>", methods=["GET"])
def review_page(response_id, question_label):
    """
    Handles the review page for a specific response and question.
    Takes in a response id (hash of the document text) and a question label to generate, validate and upload data
    to the question and review tables in DynamoDB.
    Reviews that have been not looked have a status="None", once they have been looked at, the status is set to "In Progress"
    and the data uploaded to the review table. Whether the review is Accepted or Rejected by the user is set in the
    `review_extraction` function.

    Generates booleans for:
    - whether a review has been looked at before (`entry_reviewed`)
    - whether the review is in progress (`entry_in_progress`)
    - whether the extraction is an exact match to the original document (`entry_exact_match`).

    Args:
        response_id (str): The ID of the response being reviewed.
        question_label (str): The label of the question being reviewed.
    Returns:
        werkzeug.wrappers.Response: A rendered HTML template for the review page.
    """
    logger.info("Viewing review page...")

    logger.info("Retrieving response ids and question ids from session...")
    response_ids = list(session.get("response_question_ids").keys())  # Source: Model response
    local_question_labels = session["local_question_labels"]  # Source: user .csv
    response_ids_names = {item["id"]: item["pdf_path"] for item in session.get("model_outputs")}
    logger.info("Successfully retrieved response ids and question ids from session.")

    logger.info(f"Pulling questions data from {os.environ['QUESTIONS_TABLE_NAME']}...")
    questions_schema = current_app.dynamo_db_handler.query_partition_key(
        key=response_id, key_name="response_id", table_name=os.environ["QUESTIONS_TABLE_NAME"]
    )
    logger.info("Successfully pulled questions data.")

    logger.info("Validating questions schema...")
    validated_questions_schema = [QuestionSchema(**question_schema) for question_schema in questions_schema]
    logger.info("Successfully validated questions schema.")

    # only display questions with model extraction on the review page and questions that the user uploaded
    validated_questions_schema = [
        validated_question_schema 
        for validated_question_schema 
        in validated_questions_schema 
        if validated_question_schema.question_label in local_question_labels
    ]
    
    response_question_labels = [question_schema.question_label for question_schema in validated_questions_schema]

    # There's only 1 question - response pair so taking the first value from the list
    question_schema = [schema for schema in validated_questions_schema if schema.question_label == question_label][0]

    # value to mark whether the entry has not been extracted by the model
    entry_unextracted = False
    unextracted_label = None
    if not question_schema.extracted_text:
        unextracted_label = question_label
        entry_unextracted = True
    
    logger.info(f"Pulling review data from {os.environ['REVIEW_TABLE_NAME']}...")
    entry_review = current_app.dynamo_db_handler.query_partition_key_sort_key(
        table_name=os.environ["REVIEW_TABLE_NAME"],
        partition_key="response_id",
        partition_value=response_id,
        sort_key="question_label",
        sort_value=question_label,
    )[0]
    logger.info("Successfully pulled review data.")

    logger.info("Validating review data...")
    validated_entry_review = ReviewIdSchema(**entry_review)
    logger.info("Successfully validated review data.")

    # get current status of the review
    entry_reviewed = validated_entry_review.status not in ["None", "In Progress"]
    entry_in_progress = validated_entry_review.status == "In Progress"
    entry_exact_match = any(question_schema.is_exact_match)

    validated_entry_review.reviewed_text = question_schema.exact_extracted_text

    # when a user is looking at a review pair, the status should be "In Progress" unless it's already been reviewed
    validated_entry_review.status = "In Progress" if validated_entry_review.status == "None" else validated_entry_review.status

    # Assign timestamp with start and end as the same value for validation - keeping end as None breaks the validation
    validated_entry_review.timestamp = [Decimal(str(int(datetime.now().timestamp()))), Decimal(str(int(datetime.now().timestamp())))]

    logger.info(f"Update review data to {os.environ['REVIEW_TABLE_NAME']}...")
    current_app.dynamo_db_handler.upload_data(data=validated_entry_review.model_dump(), table_name=os.environ["REVIEW_TABLE_NAME"])
    logger.info("Successfully updated review data.")

    entry_status = validated_entry_review.status

    # Rendering plaintext
    response_schema = current_app.dynamo_db_handler.query_partition_key(
        key=response_id, key_name="response_id", table_name=os.environ["RESPONSES_TABLE_NAME"]
    )
    validated_response_schema = ResponseIdSchema(**response_schema[0])
    full_response_text = bleach.clean(validated_response_schema.plain_text, strip=False)
    plaintext_holder = PlaintextHolder(full_response_text)

    search_results = []
    for search_string in question_schema.exact_extracted_text:
        search_string = bleach.clean(search_string, strip=False)
        search_results.extend(plaintext_holder.exact_text_search(search_string, max_results=None))

    if search_results:
        full_response_text = plaintext_holder.mark_text(search_results)

    return render_template(
        "review.html",
        current_page="review",
        question_schema=question_schema,
        local_question_labels=local_question_labels,
        response_ids=response_ids,
        response_id=response_id,
        response_ids_names=response_ids_names,
        question_label=question_label,
        response_question_labels=response_question_labels,
        entry_exact_match=entry_exact_match,
        entry_reviewed=entry_reviewed,
        entry_in_progress=entry_in_progress,
        entry_status=entry_status,
        entry_unextracted=entry_unextracted,
        unextracted_label=unextracted_label,
        full_response_text=full_response_text,
    )


@review_bp.route("/review/<string:current_response>/<string:question_label>/next-reponse", methods=["GET"])
def next_response_route(current_response, question_label):
    """
    Redirects to the next response page based on the given response ID and question label.

    This function retrieves a list of response IDs from the session's `response_question_ids`
    and determines the next response ID in the sequence. If the current response is the last
    in the list, it wraps around to the first response ID. It then redirects to the review
    page for the next response ID and the provided question label.

    Args:
        current_response (str): The current response ID being reviewed.
        question_label (str): The label of the question to be reviewed.

    Returns:
        werkzeug.wrappers.Response: A redirect response to the review page for the next response ID and question label.
    """
    logger.info(f"Finding next response. Old response id: {current_response}...")
    response_ids = list(session.get("response_question_ids").keys())

    response_index = response_ids.index(current_response)
    next_response_id = response_ids[response_index + 1] if response_index + 1 < len(response_ids) else response_ids[0]
    logger.info(f"Found next response. New response id: {next_response_id}")

    response_redirect = redirect(url_for("review.review_page", response_id=next_response_id, question_label=question_label))
    logger.info(f"Redirected to next response id: {next_response_id}.")

    return response_redirect


@review_bp.route("/review/<string:response_id>/<string:current_question>/next_question", methods=["GET"])
def next_question_route(response_id, current_question):
    """
    Redirects to the next question in the review process for a given response ID.

    This function retrieves the list of question labels associated with the given response ID
    from the session's `response_question_ids`. It determines the next question label in the
    sequence based on the current question label. If the current question is the last in the
    list, it wraps around to the first question label. The function then redirects to the
    review page for the next question.

    Args:
        response_id (str): The ID of the response being reviewed.
        current_question (str): The label of the current question being reviewed.

    Returns:
        werkzeug.wrappers.Response: A redirect response to the review page for the next question.
    """
    logger.info(f"Finding next question after: {current_question}")
    question_labels = session.get("response_question_ids")[response_id]

    try:
        current_index = question_labels.index(current_question)
        next_index = (current_index + 1) % len(question_labels)
        logger.info("Found next question")
        new_question_label = question_labels[next_index]
    except ValueError:  # Handle end of the question list
        logger.info("Found next question")
        new_question_label = question_labels[0]

    logger.info(f"Redirecting to next question: {new_question_label}")

    return redirect(url_for("review.review_page", response_id=response_id, question_label=new_question_label))


@review_bp.route("/review/review_extraction", methods=["POST"])
def review_extraction():
    """
    Handles the approval or rejection of the extracted text for a specific question in the review process.

    This function retrieves the response ID, question label, and action (accept or decline) from the request form.
    It updates the review data in the DynamoDB table with the new review status and the updated timestamp.
    After updating the review data, it redirects the user to the next question in the review process.

    Args:
        None (data is retrieved from the request form).

    Returns:
        werkzeug.wrappers.Response: A redirect response to the next question in the review process.
    """

    logger.info("Getting extraction data...")

    response_id = request.form.get("response_id")
    question_label = request.form.get("question_label")
    action = request.form.get("action-accept-decline")

    entry_review = current_app.dynamo_db_handler.query_partition_key_sort_key(
        table_name=os.environ["REVIEW_TABLE_NAME"],
        partition_key="response_id",
        partition_value=response_id,
        sort_key="question_label",
        sort_value=question_label,
    )[0]

    validated_entry_review = ReviewIdSchema(**entry_review)
    validated_entry_review.status = action

    validated_entry_review.timestamp[1] = Decimal(str(int(datetime.now().timestamp())))

    current_app.dynamo_db_handler.upload_data(data=validated_entry_review.model_dump(), table_name=os.environ["REVIEW_TABLE_NAME"])

    logger.info(f"Updated review status to {action} for response {response_id}, question {question_label}")

    return redirect(url_for("review.next_question_route", response_id=response_id, current_question=question_label))
