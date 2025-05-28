from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class QuestionAnswer(BaseModel):
    """
    QuestionAnswer is a Pydantic model that represents a question and its extracted answer(s).

    Attributes:
        question_label (str): The label identifying the question.
        question_text (str): The text of the question, e.g., "Do you agree with X?".
        extracted_text (str): A list of extracted answers to the question or an empty list if no answer. Multiple list elements are used when
        there are answers from separate parts of the text.
        extracted_text_similarity (List[Decimal]): A list of similarity scores between the original extracted text and the new extracted text.
    """

    model_config = ConfigDict(coerce_numbers_to_str=True)

    question_label: str = Field(..., description="The label identifying the question.")
    question_text: str = Field(..., description='The question text, e.g. "Do you agree with X?".')
    extracted_text: List[str] = Field(
        ...,
        description="A list of extracted answers to the question or an empty list if no answer. Multiple list elements are used when there are answers from separate parts of the text.",  # noqa: E501
    )
    original_extracted_text: Optional[List[str]] = Field(
        [],
        description="""
        A store for the model's original extracted text.
        Used to keep hold of the original response if the extracted text isn't in the PDF.
        """,
    )
    extracted_text_similarity: Optional[List[Decimal]] = Field(
        [],
        description="""
        A list of similarity scores between the original extracted text and the new extracted text.
        """,
    )


class QuestionAnswers(BaseModel):
    """
    QuestionAnswers is a model that represents a collection of question-answer elements.

    Attributes:
        question_answers (List[QuestionAnswer]): A list of question-answer elements.
        count_retries (Decimal): The number of times the model has retried extracting the answers.
    """

    question_answers: List[QuestionAnswer] = Field(..., description="A list of question-answer elements.")
    count_retries: Decimal = Field(Decimal("0"), description="The number of times the model has retried extracting the answers.")
