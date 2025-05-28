from flask import Blueprint, Response, current_app

viewer = Blueprint("viewer", __name__, template_folder="templates")

@viewer.route("/<path:s3_file_path>")
def view_s3_file(s3_file_path: str):
    s3_object = current_app.storage_handler.get_object(key=s3_file_path)
    file_content = s3_object["Body"].read()
    content_type = s3_object["ContentType"]

    headers = {
        "Content-Disposition": "inline", 
        "Content-Type": "application/pdf" if s3_file_path.endswith(".pdf") else content_type
    }

    return Response(file_content, headers=headers)