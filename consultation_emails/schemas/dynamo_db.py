"""
This module defines Pydantic schemas for various data structures used in the consultation email extraction process.
Classes:
    ModelOutputsSchema: Pydantic schema for the model outputs stored in the DynamoDB table.
    ReviewIdSchema: Pydantic schema for individual review data.
    QuestionSchema: Pydantic schema for a questions and responses. Includes ReviewIdSchema and ManualIdSchema as children.
    ManualIdSchema: Pydantic schema for a collection of manual tagging data.
    ResponseIdSchema: Pydantic schema for the response data. Includes QuestionSchema as a child.

Example usage:
# Creating an instance of ReviewIdSchema
review_id = {
    "response_id": "hash123",
    "question_label": "Q1.1.1",
    "user_id": "user123",
    "timestamp": [1710720000, 1710723600],
    "reviewed_text": "test text",
    "status": "Accepted"
}

review_id_schema = ReviewIdSchema(**review_id)

# Creating an instance of ManualIdSchema
manual_id = {
    "response_id": "hash123",
    "question_label": "Q1.1.1",
    "user_id": "user123",
    "timestamp": [1710720000, 1710723600],
    "manual_text": "manually added text",
    "status": True
}

manual_id_schema = ManualIdSchema(**manual_id)

# Creating an instance of QuestionSchema
question = {
    "response_id": "hash123",
    "question_label": "Q1.1.1",
    "question_text": "What is the main topic?",
    "extracted_text": ["foo text"],
    "exact_extracted_text": ["foo text"],
    "is_exact_match": True,
    "jaccard_similarity": Decimal("0.5"),
    "string_start_end_loc": [[100, 200]]
}

question_schema = QuestionSchema(**question)

# Creating an instance of ResponseIdSchema
response = {
    "response_id": "hash123",
    "timestamp": 1710720000,
    "model": "gpt-4",
    "prompt_template": ["templates/extraction.txt", "v1.0"],
    "plain_text": "Original document text here",
    "retries": 1,
    "completed": False
}

response_id_schema = ResponseIdSchema(**response)

"""

from decimal import Decimal
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


class ModelOutputsSchema(BaseModel):
    """
    Pydantic schema for the model outputs stored: consultation-data-dev-dynamodb
    """

    id: str = Field(..., description="Partion Key. A unique PDF ID created by hashing the contents of the PDF file")
    processed_datetime: int = Field(..., description="Sort Key. The datetime the PDF file was processed by the model")
    item: Union[dict, list] = Field(..., description="The model extractions built from QuestionAnswers class")
    metadata: dict = Field(..., description="Metadata about the model extraction")
    count_retries: Decimal = Field(..., description="Number of retries by the model to produce the responses in `item`")


class ReviewIdSchema(BaseModel):
    """
    Pydantic schema for the review data. This is for each review that is processed.
    """

    response_id: str = Field(None, description="Partion Key. A unique response ID created by hashing the contents of the response file")
    question_label: str = Field(None, description="Sort Key. The question label taken from the user input list of questions")
    user_id: str = Field(None, description="The user ID of the reviewer")
    timestamp: Optional[list[Decimal]] = Field(None, description="List of the start and finish datetime of when the review is processed")
    reviewed_text: list[str] = Field(None, description="The text that the user has reviewed")
    status: Literal["Accepted", "Rejected", "Modified", "In Progress", "None"] = Field(
        "None", description="The status of the review. This can be 'None', 'Accepted', 'Rejected' or 'Modified'"
    )  # noqa: E501


class ManualIdSchema(BaseModel):
    """
    Pydantic schema for unique user manual extraction data.
    """

    response_id: str = Field(None, description="Partion Key. A unique response ID created by hashing the contents of the response file")
    question_label: str = Field(None, description="Sort Key. The question label taken from the user input list of questions")
    user_id: str = Field(None, description="The user ID of the reviewer")
    timestamp: Optional[list[Decimal]] = Field(None, description="List of the start and end datetime of when the review is processed")
    manual_text: Optional[str] = Field(
        None,
        description="The text that the user has manually added to the extraction response. This is optional as user may not always have manual additions",  # noqa: E501
    )
    status: Literal["Original", "Modified"] = Field(
        None,
        description="The status of the manual extractions. This can be 'Original', meaning no manual extraction is required and so uses the original reviewed extraction, or 'Modified', meaning a manual extraction has been used.",  # noqa: E501
    )


class QuestionSchema(BaseModel):
    response_id: str = Field(None, description="Partion Key. A unique response ID created by hashing the contents of the response file")
    timestamp: int = Field(None, description="The datetime the response file was processed by the model")
    question_label: str = Field(None, description="Sort Key. The question label taken from the user input list of questions")
    question_text: str = Field(None, description="The question text taken from the user input list of questions")
    extracted_text: list[str] = Field(None, description="The extracted text from the response file by the model")
    exact_extracted_text: list[str] = Field(
        None,
        description="The extracted text from the response file by the model. This can be either the model's exact response or the most similar extract using Jaccard",  # noqa: E501
    )
    is_exact_match: list[bool] = Field(None, description="Boolean to indicate if the extracted text is an exact match to the response file")
    jaccard_similarity: list[Decimal] = Field(None, description="The Jaccard similarity score between the extracted text and the response file")
    string_start_end_loc: Optional[list[list[int]]] = Field(
        None, description="The start and end location of the extracted text in the response file"
    )


class ResponseIdSchema(BaseModel):
    response_id: str = Field(None, description="Partion Key. A unique response ID created by hashing the contents of the response file")
    timestamp: int = Field(None, description="The datetime the response file was processed by the model")
    model: list[str] = Field(None, description="The LLM used to process the response file")
    prompt_template: list[Optional[str]] = Field(None, description="The prompt template path and its version")
    plain_text: str = Field(None, description="The plain text extracted from the response file")
    retries: int = Field(
        None,
        description="Number of retries by the model to produce the responses. Retries can be caused by the model outputs not conforming to the schema",  # noqa: E501
    )
    completed: bool = Field(False, description="Boolean to indicate if the review has been completed")
