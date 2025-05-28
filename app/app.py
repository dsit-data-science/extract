from flask import Flask
from flask_session import Session

from consultation_emails.database.fetch_data import DynamoDbHandler, StorageHandler
from consultation_emails.extract.question_extraction_api import LangchainExtractor, ResponseUploader
from consultation_emails.schemas.dynamo_db import ManualIdSchema, ResponseIdSchema, ReviewIdSchema


def create_app():
    """
    Create and configure the Flask application.
    This function initializes the Flask application, loads the configuration
    from the 'config.Config' object, and registers the necessary blueprints
    for different parts of the application.
    Blueprints registered:
    - upload_bp: Handles file uploads.
    - viewer: Handles viewing functionality, accessible via the '/viewer' URL prefix.
    - langchain_bp: Handles langchain related routes.
    - review_bp: Handles review page related routes.
    - manual_extraction_bp: Handles manual extraction related routes.
    Returns:
        Flask: The configured Flask application instance.
    """

    app = Flask(__name__)
    app.config.from_object("config.Config")
    app.config["SESSION_TYPE"] = "filesystem"
    Session(app)

    app.storage_handler = StorageHandler()
    app.dynamo_db_handler = DynamoDbHandler()
    app.extractor = LangchainExtractor()
    app.response_uploader = ResponseUploader(dynamo_db_handler=app.dynamo_db_handler)
    app.review_id_schema = ReviewIdSchema()
    app.manual_id_schema = ManualIdSchema()
    app.response_id_schema = ResponseIdSchema()

    # Register Blueprints
    from blueprints.upload.routes import upload_bp

    app.register_blueprint(upload_bp)

    from blueprints.viewer.routes import viewer

    app.register_blueprint(viewer, url_prefix="/viewer")

    from blueprints.langchain.routes import langchain_bp

    app.register_blueprint(langchain_bp)

    from blueprints.review.routes import review_bp

    app.register_blueprint(review_bp)

    from blueprints.manual_extraction.routes import manual_extraction_bp

    app.register_blueprint(manual_extraction_bp)

    from blueprints.download.routes import download_bp

    app.register_blueprint(download_bp)

    @app.template_global()
    def is_dev():
        return app.config["ENV"] == "dev"

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
