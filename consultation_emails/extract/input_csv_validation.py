"""
Function pulls from the "CsvValidator" schema in consultation_emails/schemas/input_data.py to validate the input CSV file.
Likely this script will not be needed in future dev and integrated elsewhere, but storing here for now.
"""

import pandas as pd

from consultation_emails.schemas.input_data import CsvValidator


def validate_csv(file):
    """
    Validates the content of a CSV file.
    Uses the _process_csv helper function to perform the validation.

    Args:
        file (str or file): The file path or file object to validate.
    """
    if isinstance(file, str):
        with open(file) as csvfile:  # Ensure safe file handling
            return _process_csv(csvfile)  # Process inside helper function
    else:
        return _process_csv(file)  # Already an open file, just process it


def _process_csv(csvfile):
    """
    Processes and validates the content of a CSV file.

    This function performs the following validations:
    1. Detects and raises an error if any column headers contain leading or trailing whitespace.
    2. Normalizes column headers by stripping leading and trailing whitespace.
    3. Checks for the presence of required columns ('question_label' and 'question_text') and raises an error if any are missing.
    4. Checks for the presence of any extra columns and raises an error if any are found.
    5. Checks that the 'question_label' column has unique values.
    6. Validates each row of the CSV file using the Pydantic schema 'CsvValidator'.

    """
    df = pd.read_csv(csvfile, delimiter=",")
    original_headers = df.columns.tolist()
    required_columns = {"question_label", "question_text"}

    # Detect leading/trailing whitespace in column headers
    bad_headers = [col for col in original_headers if col.strip() != col]
    if bad_headers:
        raise ValueError(f"Column headers contain leading or trailing whitespace: {', '.join(bad_headers)}.")

    # Normalize headers
    stripped_headers = {col.strip() for col in original_headers}

    # Check for missing columns
    missing_columns = required_columns - stripped_headers
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing_columns))}.")

    # Check for extra columns
    extra_columns = stripped_headers - required_columns
    if extra_columns:
        raise ValueError(
            f"Unexpected extra columns present: {', '.join(sorted(extra_columns))}. Only {', '.join(sorted(required_columns))} are allowed."
        )

    # Check that question_label has unique values
    if not df["question_label"].is_unique:
        raise ValueError("The question_label column must have unique values.")

    # Validate rows using Pydantic
    data = [CsvValidator.model_validate(row) for row in df.to_dict(orient="records")]

    return data
