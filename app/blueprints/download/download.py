import os

import pandas as pd
from flask import (
    current_app,
    session,
)

from consultation_emails.database.fetch_data import DynamoDbHandler
from consultation_emails.logger.logger import logger


def get_session_question_ids():
    """
    Retrieves the active question IDs from the session.

    Returns:
        list: A list of question IDs.
    """
    return [item["question_label"] for item in session.get("local_questions", [])]


def get_session_response_ids():
    """
    Retrieves the active response IDs from the session.

    Returns:
        list: A list of response IDs.
    """
    response_question_ids = session.get("response_question_ids", {})
    return [response_id for response_id, _question_labels in response_question_ids.items()]


def query_question_answers(
    dynamo_db_handler: DynamoDbHandler,
    response_id: str,
    table_name: str,
    table_key_name: str = "response_id",
    flatten: bool = False,
    convert_decimal: bool = True,
):
    """
    Queries the questions table in DynamoDB for a specific response ID.

    Args:
        dynamo_db_handler (DynamoDbHandler): The DynamoDB handler instance.
        response_id (str): The response ID to query.
        table_name (str): The name of the DynamoDB table.
        table_key_name (str): The key name for the partition key.

    Returns:
        list: A list of question schema dictionaries for the specified response ID.
    """
    questions_schema = dynamo_db_handler.query_partition_key(key=response_id, key_name=table_key_name, table_name=table_name)
    keys_to_keep = [
        "response_id",
        "question_label",
        "extracted_text",
        "exact_extracted_text",
        "is_exact_match",
        "jaccard_similarity",
        "question_text",
    ]
    # Convert to DataFrame and filter columns
    df = pd.DataFrame(questions_schema)
    df = df[[k for k in keys_to_keep if k in df.columns]]

    if convert_decimal and "jaccard_similarity" in df.columns:
        df["jaccard_similarity"] = df["jaccard_similarity"].apply(lambda x: [float(i) for i in x])

    if flatten:
        list_cols = ["extracted_text", "exact_extracted_text", "is_exact_match", "jaccard_similarity"]
        existing_list_cols = [col for col in list_cols if col in df.columns]
        df = df.explode(existing_list_cols, ignore_index=True)

    return df.to_dict(orient="records")


def query_manual_review(
    dynamo_db_handler: DynamoDbHandler, response_id: str, table_name: str, table_key_name: str = "response_id", convert_decimal: bool = True
):
    """
    Queries the manual review table in DynamoDB for a specific response ID.
    Args:
        dynamo_db_handler (DynamoDbHandler): The DynamoDB handler instance.
        response_id (str): The response ID to query.
        table_name (str): The name of the DynamoDB table.
        table_key_name (str): The key name for the partition key.
    Returns:
        list: A list of review schema dictionaries for the specified response ID.
    """

    review_schema = dynamo_db_handler.query_partition_key(key=response_id, key_name=table_key_name, table_name=table_name)
    keys_to_keep = {
        "response_id",
        "question_label",
        "user_id",
        "timestamp",
        "manual_text",
        "status",
    }
    review_schema = [{k: v for k, v in item.items() if k in keys_to_keep} for item in review_schema]

    if convert_decimal:
        for item in review_schema:
            if item["timestamp"] is not None:
                start_time = item["timestamp"][0]
                end_time = item["timestamp"][1]
                item["timestamp"] = [float(start_time) if start_time is not None else None, float(end_time) if end_time is not None else None]
            else:
                item["timestamp"] = None
    return review_schema


def query_reviews(
    dynamo_db_handler: DynamoDbHandler,
    response_id: str,
    table_name: str,
    table_key_name: str = "response_id",
    convert_decimal: bool = True,
    status_filter=None,
):
    """
    Queries the review table in DynamoDB for a specific response ID.
    Args:
        dynamo_db_handler (DynamoDbHandler): The DynamoDB handler instance.
        response_id (str): The response ID to query.
        table_name (str): The name of the DynamoDB table.
        table_key_name (str): The key name for the partition key.
        status_filter (str or list[str], optional): The status to filter reviews by. Defaults to None.
    Returns:
        list: A list of review schema dictionaries for the specified response ID.
    """

    if status_filter is not None:
        assert isinstance(status_filter, (str, list)), "status_filter should be a string or a list of strings"
        if isinstance(status_filter, str):
            status_filter = {status_filter}
        assert all(isinstance(status, str) for status in status_filter), "status_filter should be a string or a list of strings"

        status_filter = set(status_filter)

    review_schema = dynamo_db_handler.query_partition_key(key=response_id, key_name=table_key_name, table_name=table_name)

    keys_to_keep = {
        "response_id",
        "question_label",
        "user_id",
        "timestamp",
        "reviewed_text",
        "status",
    }
    review_schema = [{k: v for k, v in item.items() if k in keys_to_keep} for item in review_schema]

    if status_filter is not None:
        review_schema = [item for item in review_schema if "status" in item and item["status"] in status_filter]

    if convert_decimal:
        for item in review_schema:
            if item["timestamp"] is not None:
                start_time = item["timestamp"][0]
                end_time = item["timestamp"][1]
                item["timestamp"] = [float(start_time) if start_time is not None else None, float(end_time) if end_time is not None else None]
            else:
                item["timestamp"] = None
    return review_schema


def get_session_reviews():
    """
    Retrieves the review data for the current session.

    Returns:
        pd.DataFrame: A DataFrame containing the review data.
    """
    dataset = []
    review_dataset = []

    for response_id in get_session_response_ids():
        logger.info(f"Fetching response data for response_id: {response_id}")
        dataset.extend(
            query_question_answers(
                dynamo_db_handler=current_app.dynamo_db_handler,
                response_id=response_id,
                table_name=os.environ["QUESTIONS_TABLE_NAME"],
                flatten=False,
            )
        )

        review_dataset.extend(
            query_reviews(
                dynamo_db_handler=current_app.dynamo_db_handler,
                response_id=response_id,
                table_name=os.environ["REVIEW_TABLE_NAME"],
                status_filter=["Accepted"],
            )
        )

    dataset_df = pd.DataFrame(dataset)
    review_dataset_df = pd.DataFrame(review_dataset, columns=["response_id", "question_label", "status"])

    # Filter to question IDs that are valid for the session
    session_question_ids = get_session_question_ids()
    dataset_df = filter_and_sort(dataset_df, question_ids=session_question_ids)

    # Join for the review status column
    dataset_df = pd.merge(
        dataset_df,
        review_dataset_df,
        how="left",
        left_on=["response_id", "question_label"],
        right_on=["response_id", "question_label"],
        suffixes=(None, "_review"),
    )
    # Transform to join the list into a string
    dataset_df["exact_extracted_text"] = dataset_df["exact_extracted_text"].apply(lambda x: "" if x is None else "\n".join(x))

    # Empty the strings of values without accepted reviews
    dataset_df["exact_extracted_text"] = dataset_df["exact_extracted_text"].where(dataset_df["status"].notna(), "")

    # Select only the relevant columns
    dataset_df = dataset_df[["response_id", "question_label", "question_text", "exact_extracted_text"]]
    return dataset_df


def get_session_manual_reviews():
    """
    Retrieves the manual review data for the current session.

    Returns:
        pd.DataFrame: A DataFrame containing the manual review data.
    """
    logger.info("Generating manual review dataset for download...")

    dataset = []
    for response_id in get_session_response_ids():
        logger.info(f"Fetching manual review data for response_id: {response_id}")
        dataset.extend(
            query_manual_review(
                dynamo_db_handler=current_app.dynamo_db_handler,
                response_id=response_id,
                table_name=os.environ["MANUAL_TABLE_NAME"],
            )
        )

    dataset_df = pd.DataFrame(dataset)
    # Filter to question IDs that are valid for the session
    dataset_df = filter_and_sort(dataset_df, question_ids=get_session_question_ids())
    dataset_df = dataset_df[dataset_df["status"] == "Modified"]
    return dataset_df


def filter_and_sort(dataset: pd.DataFrame, question_ids: list = None, ascending: bool = True):
    """
    Helper function to filter and sort the dataset based on response ids and question IDs. The same order as provided in the question_ids list
    is maintained.

    Args:
        dataset (pd.DataFrame): The dataset to be filtered and sorted. The column names 'response_id' and 'question_label' are required.
        question_ids (list): The list of question IDs to filter the dataset.
        ascending (bool): Whether to sort in ascending order. Defaults to True.
    Returns:
        pd.DataFrame: The filtered and sorted dataset.
    """
    if question_ids is None:
        dataset = dataset.sort_values(by=["response_id"], ascending=ascending)
        return dataset

    else:
        # Ensure question_ids is a list
        assert isinstance(question_ids, list), "question_ids should be a list"

        # Filter to question IDs that are valid for the session
        dataset = dataset[dataset["question_label"].isin(question_ids)]

        # Sort values by response id and question label (the Categorical is used to maintain the order of question_ids)
        dataset["question_label"] = pd.Categorical(dataset["question_label"], categories=question_ids, ordered=True)
        dataset = dataset.sort_values(by=["response_id", "question_label"], ascending=ascending)

        return dataset


def merge_datasets(review_df, manual_df):
    """
    Merges the review DataFrame with the manual review DataFrame to create a dataset suitable for download.
    The resulting DataFrame will have response_id, question_label, question_text, and exact_extracted_text columns.
    The exact_extracted_text will contain the extracted text for each question, and if there is a manual review,
    the manual review text will be appended to it.

    Args:
        review_df (pd.DataFrame): The DataFrame containing the review data.
        manual_df (pd.DataFrame): The DataFrame containing the manual review data.
    Returns:
        pd.DataFrame: A DataFrame containing the merged dataset with response_id, question_label, question_text, and exact_extracted_text.
    """
    # Join the manual review text onto the text
    dataset_df = pd.merge(
        review_df,
        manual_df[["response_id", "question_label", "manual_text"]],
        how="left",
        left_on=["response_id", "question_label"],
        right_on=["response_id", "question_label"],
        suffixes=("", "_manual_review"),
    )

    dataset_df["exact_extracted_text"] = dataset_df["exact_extracted_text"].str.cat(
        dataset_df["manual_text"].fillna(""),
        sep="\n",
        na_rep="",
    )

    # Strip whitespace-only values to empty strings
    dataset_df["exact_extracted_text"] = dataset_df["exact_extracted_text"].str.strip()

    dataset_df = dataset_df.pivot(index="response_id", columns=["question_label", "question_text"], values="exact_extracted_text")

    # Flatten columns to just use question_text (level 1)
    dataset_df.columns = [col[1] for col in dataset_df.columns]

    # Reset the index to make response_id a column
    dataset_df = dataset_df.reset_index()
    return dataset_df
