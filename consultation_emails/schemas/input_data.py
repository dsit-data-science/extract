'''
This script takes a CSV input and validates the file based on the following criteria:
- The CSV file must have the correct headers.
- The fields in the CSV file cannot be empty or have whitespace.
- The CSV columns must be of class "str".

The script uses the Pydantic (v2) library to define a schema for the CSV data validation.
The `CsvValidator` class defines the structure of the CSV data.
'''

from pydantic import BaseModel, field_validator


class CsvValidator(BaseModel):
    """
    Pydantic schema to validate the CSV data.
    Ensures:
    - Fields are non-empty.
    - Fields do not contain only whitespace.
    - Fields are stripped of leading/trailing whitespace.
    - 'NaN' and 'None' are treated as missing.

    Attributes:
        question_label (str): The ID of the question.
        question_text (str): The text of the question
    """

    question_label: str
    question_text: str

    @field_validator("question_label", "question_text", mode="before")
    @classmethod
    def validate_non_empty(cls, value, info):
        """
        - Converts 'NaN' and 'None' to actual None.
        - Strips leading/trailing whitespace.
        - Ensures field is not empty.

        Args:
            cls (class): The class of the model.
            value (str): The value of the field.
            info (dict): Information about the field.
        """
        if value is None or str(value).strip().lower() in {"nan", "none", ""}:
            raise ValueError(f"Field '{info.field_name}' cannot be empty or contain 'NaN'.")

        return str(value).strip()  #  Trim spaces before validation


