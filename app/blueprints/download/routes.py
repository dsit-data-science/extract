from blueprints.download.download import get_session_manual_reviews, get_session_reviews, merge_datasets
from flask import (
    Blueprint,
    Response,
    render_template,
)

from consultation_emails.logger.logger import logger

download_bp = Blueprint("download", __name__, template_folder="templates")


@download_bp.route("/download_dataset_page", methods=["GET"])
def download_dataset_page():
    """
    Renders the download dataset page.

    Returns:
        flask.Response: The rendered HTML page for downloading datasets.
    """
    return render_template("download_dataset.html", current_page="download_dataset")


@download_bp.route("/download_question_answers_pivot", methods=["GET"])
def download_question_answers_pivot():
    """
    Downloads a dataset in CSV form containing valid response IDs, all question IDs (including unanswered),
    and extracted answers (empty string for unanswered questions).

    The columns are response_id and the text of each question. The cell values for questions are the extracted text for the question and
    response.

    When a question has a manual review, the manual review text is appended to the extracted text.

    Returns:
        flask.Response: A CSV file containing the dataset.
    """
    logger.info("Generating dataset for download...")
    review_df = get_session_reviews()
    manual_df = get_session_manual_reviews()
    dataset_df = merge_datasets(review_df, manual_df)
    dataset_csv = dataset_df.to_csv(index=False, header=True)
    logger.info("Dataset generated successfully.")
    # Return CSV as a downloadable file
    return Response(
        dataset_csv,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=qualtrics_output.csv"},
    )
