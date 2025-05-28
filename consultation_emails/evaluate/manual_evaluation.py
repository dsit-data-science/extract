"""
Using DeepEvals Answer Relevancy Metric to evaluate the quality of the extractions from the LLM.
Specifically scoring how relevant the extracted text is to the question, on a scale from 0-1.
The exractions getting evaluated are pulled from a DynamoDB table, and the relevancy is evaluated using the Azure OpenAI model.

Example usage:
    .. code-block:: python
        from consultation_emails.evaluate.manual_evaluation import (
            DeepEvalAzureOpenAI,
            evaluate_answer_relevancy,
            get_question_answers,
            relevancy_test_cases,
        )

        # Load table name
        response_id = "7203a1c7fa6f9b57ca97f3deebbbd93d21c7ed0ad54a308b2e59bec32acb9003"
        key_name = "response_id"
        table_name = "extract-questions"

        # Extract data from the database
        formatted_data = get_question_answers(response_id, key_name, table_name)
        print(f"extracted_data: {formatted_data}")

        # create test cases
        deepeval_test_cases = relevancy_test_cases(formatted_data)
        print(f"test_cases: {deepeval_test_cases}")

        # evaluate the relevancy of the answers
        azure_openai = DeepEvalAzureOpenAI()
        threshold = 0.7
        results = evaluate_answer_relevancy(deepeval_test_cases, azure_openai, threshold=threshold)
        print(f"relevancy_results: {results}")

    Full pipeline example
    .. code-block:: python

        import pandas as pd
        from consultation_emails.evaluate.manual_evaluation import run_pipeline_and_evaluate

        # All in one pipeline
        document_filepath = "dcmsdataprotectionreformsconsultation_amrcresponse_final.pdf"
        csv_filepath = "data_reform_questions_test.csv"
        system_prompt_template_path = "prompt_templates/approved/prompt_template_system.jinja"
        human_prompt_template_path = "prompt_templates/approved/prompt_template_human.jinja"

        results_file = run_pipeline_and_evaluate(
            document_filepath=document_filepath,
            csv_filepath=csv_filepath,
            system_prompt_template_path=system_prompt_template_path,
            human_prompt_template_path=human_prompt_template_path,
            threshold=0.7,
            use_database=False,
        )

        # Display results as a DataFrame
        print(pd.DataFrame(results_file))

        # All in one pipeline with database
        response_id = "7203a1c7fa6f9b57ca97f3deebbbd93d21c7ed0ad54a308b2e59bec32acb9003"
        key_name = "response_id"
        table_name = "extract-questions"

        results_db = run_pipeline_and_evaluate(
            response_id=response_id,
            key_name=key_name,
            table_name=table_name,
            threshold=0.7,
            use_database=True,
        )

        # Display database results as a DataFrame
        print(pd.DataFrame(results_db))
"""  # noqa: E501

import os

from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

from consultation_emails.database.fetch_data import DynamoDbHandler, SecretsManagerHandler

load_dotenv()

dynamo_db_handler = DynamoDbHandler()
secrets_manager_handler = SecretsManagerHandler()


class DeepEvalAzureOpenAI(DeepEvalBaseLLM):
    """
    Class for the Azure OpenAI model to be used with DeepEval.
    A custom implementation of the DeepEvalBaseLLM class to allow for the Azure OpenAI model to be used with DeepEval.
    Inherits from the DeepEvalBaseLLM class, to ensure compatibility with the DeepEval functions.
    """

    def __init__(self):
        """
        Initialize the DeepEvalAzureOpenAI class with a model.

        Args:
            model: The model instance to be used for generating responses.
        """
        secret_id = os.environ.get("MODEL_SECRETS_ID", "extract-secrets")
        secrets = secrets_manager_handler.get_secret_value(secret_id=secret_id)

        openai_api_version = secrets["AZURE_OPENAI_API_VERSION"]
        azure_deployment = secrets["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
        azure_endpoint = secrets["AZURE_OPENAI_ENDPOINT"]
        openai_api_key = secrets["AZURE_OPENAI_API_KEY"]

        self.model = AzureChatOpenAI(
            openai_api_version=openai_api_version,
            azure_deployment=azure_deployment,
            azure_endpoint=azure_endpoint,
            openai_api_key=openai_api_key,
        )

    def load_model(self):
        """
        Load model instance.
        """
        pass

    def generate(self, prompt: str) -> str:
        """
        Generate a response from the model based on the given prompt.

        Args:
            prompt (str): The input prompt to generate a response for.
        """
        return self.model.invoke(prompt).content

    async def a_generate(self, prompt: str) -> str:
        """
        Asynchronously generate a response from the model based on the given prompt.

        Args:
            prompt (str): The input prompt to generate a response for.

        """
        res = await self.model.ainvoke(prompt)
        return res.content

    def get_model_name(self):
        """
        Retrieve the name of the model.
        """
        return "Custom Azure OpenAI Model"


def format_question_answers(data: list[dict], model_text: bool = True, exact_text: bool = False):
    """
    Format question and answer data from a DynamoDB table for the relevancy_test_cases function.

    The list items are required to have these fields:
        {
            "response_id": str,
            "question_label": str,
            "question_text": str,
            "extracted_text": list[str],
            "exact_extracted_text": list[str]
            "timestamp": int,
        }
    Args:
        data (list): A list of dictionaries matching the format above.
        model_text (bool): Flag to include model text in the output. Defaults to True.
        exact_text (bool): Flag to include exact quoted text in the output. Defaults to False.
    Returns:
        list: A list of dictionaries containing formatted question and answer data.
        Each dictionary contains:
            - "response_id" (str): The response ID.
            - "timestamp" (int): The timestamp of the response.
            - "question_label" (str): The label of the question.
            - "question_text" (str): The text of the question.
            - "answer" (list[str]): The extracted answer(s).
            - "text_type" (str): The type of text ("model" or "exact")
    """

    formatted_data = []
    if model_text:
        formatted_data = formatted_data + [
            {
                "response_id": item["response_id"],
                "timestamp": round(item["timestamp"]),  # Converting from Decimal which is not JSON serializable
                "question_label": item["question_label"],
                "question_text": item["question_text"],
                "answer": item["extracted_text"],
                "text_type": "model",
            }
            for item in data
        ]

    if exact_text:
        formatted_data = formatted_data + [
            {
                "response_id": item["response_id"],
                "timestamp": round(item["timestamp"]),  # Converting from Decimal which is not JSON serializable
                "question_label": item["question_label"],
                "question_text": item["question_text"],
                "answer": item["exact_extracted_text"],
                "text_type": "exact",
            }
            for item in data
        ]

    return formatted_data


def get_question_answers(
    response_id: str,
    key_name: str,
    table_name: str = None,
    model_text: bool = True,
    exact_text: bool = False,
):
    """
    Retrieve and format question and answer data from a DynamoDB table for the relevancy_test_cases function.

    The table items are required to have these fields:
    {
        "response_id": str,
        "question_label": str,
        "question_text": str,
        "extracted_text": list[str],
        "exact_extracted_text": list[str]
        "timestamp": int,
    }
    Args:
        response_id (str): The hash ID of the file to query.
        key_name (str): The key name to use for the query.
        table_name (str): The name of the DynamoDB table. If None, the environment variable "QUESTIONS_TABLE_NAME" is used.
        model_text (bool): Flag to include model text in the output. Defaults to True.
        exact_text (bool): Flag to include exact quoted text in the output. Defaults to False.
    Returns:
        list: A list of dictionaries containing formatted question and answer data.
        Each dictionary contains:
            - "response_id" (str): The response ID.
            - "timestamp" (int): The timestamp of the response.
            - "question_label" (str): The label of the question.
            - "question_text" (str): The text of the question.
            - "answer" (list[str]): The extracted answer(s).
            - "text_type" (str): The type of text ("model" or "exact").
    """

    if table_name is None:
        table_name = os.environ["QUESTIONS_TABLE_NAME"]

    if not model_text and not exact_text:
        return []

    # Query all items for the given partition key
    data = dynamo_db_handler.query_partition_key(response_id, key_name, table_name, ascending=False)

    formatted_data = format_question_answers(data, model_text=model_text, exact_text=exact_text)

    return formatted_data


def relevancy_test_cases(formatted_data: list, join_list: bool = True):
    """
    Generate test cases for relevancy evaluation based on formatted data.
    Args:
        formatted_data (list): A list of dictionaries, where each dictionary contains:
            - "response_id" (str): The response ID.
            - "timestamp" (optional, int): The timestamp of the response.
            - "question_label" (str): The label of the question.
            - "question_text" (str): The text of the question.
            - "answer" (str or list): The extracted answers, which can be an empty string, a single string, or a list of strings.
            - "text_type" (optional, str): The type of text ("model" or "exact").
        join_list (bool): Flag to determine whether to join answer lists into a single string.
    Returns:
        list: A list of LLMTestCase instances, each representing a test case with:
            - input (str): The question text.
            - actual_output (str): The corresponding answer (or an empty string if no answer is provided).
            - additional_metadata (dict): Metadata including the question label and other data fields.
    """

    test_cases = []

    for item in formatted_data:
        question_label = item["question_label"]
        question_text = item["question_text"]
        answers = item["answer"]

        additional_metadata = {
            "response_id": item["response_id"],
            "timestamp": item.get("timestamp"),
            "question_label": question_label,
            "text_type": item.get("text_type", "Unknown"),
        }

        # Ensure answers is always treated as a list
        if not isinstance(answers, list):
            answers = [answers]

        # If no answer is provided (empty list), create a test case with an empty string
        if not answers:
            test_cases.append(
                LLMTestCase(
                    input=question_text,
                    actual_output="",  # Empty output
                    additional_metadata=additional_metadata,
                )
            )
        elif join_list:
            # Join the answers into a single string if specified
            answer_text = "\n".join(answers)
            test_cases.append(
                LLMTestCase(
                    input=question_text,
                    actual_output=answer_text,
                    additional_metadata=additional_metadata,
                )
            )
        else:
            for answer in answers:
                test_cases.append(LLMTestCase(input=question_text, actual_output=answer, additional_metadata=additional_metadata.copy()))

    return test_cases


def evaluate_answer_relevancy(test_cases: list, model: DeepEvalBaseLLM = None, threshold: float = 0.7):
    """
    Runs DeepEval's Answer Relevancy test on the given test cases and returns detailed results.

    Args:
        test_cases (list): List of LLMTestCase objects.
        model (DeepEvalBaseLLM, optional): The LLM model to use for evaluation (e.g., Azure OpenAI instance). If None, a default model is used.
        threshold (float): The minimum relevancy score required to pass.

    Returns:
        list: A list of dictionaries, each containing:
            - "response_id" (str): The response ID.
            - "timestamp" (int): The timestamp of the response.
            - "question_label" (str): The label of the question.
            - "text_type" (str): The type of extracted text ("model" or "exact").
            - "input" (str): The question text.
            - "actual_output" (str): The corresponding answer.
            - "score" (float): The relevancy score.
            - "reason" (str): The reason for the score.
    """

    if model is None:
        model = DeepEvalAzureOpenAI()

    # Add Answer Relevancy Metric to each test case
    relevancy_metric = AnswerRelevancyMetric(threshold=threshold, model=model, include_reason=True)
    results = evaluate(test_cases, [relevancy_metric], print_results=False)
    results = results.model_dump()

    detailed_results = []

    test_results = results["test_results"]
    # re-sort according to the name field (e.g. test_case_0) to correct the order
    test_results = sorted(test_results, key=lambda x: int(x["name"].split("_")[-1]))

    for test_case, test_result in zip(test_cases, test_results):
        in_text = test_result["input"]
        out_text = test_result["actual_output"]
        metadata = test_case.additional_metadata

        detailed_results.append(
            {
                "response_id": metadata["response_id"],
                "timestamp": metadata.get("timestamp"),
                "question_label": metadata.get("question_label", "Unknown"),
                "text_type": metadata.get("text_type", "Unknown"),
                "input": in_text,
                "actual_output": out_text,
                "deepeval_relevancy_score": test_result["metrics_data"][0]["score"],
                "deepeval_relevancy_reason": test_result["metrics_data"][0]["reason"],
            }
        )

    return detailed_results


def run_pipeline_and_evaluate(
    response_id: str = None,
    key_name: str = None,
    table_name: str = None,
    threshold: float = 0.7,
    model_text: bool = True,
    exact_text: bool = False,
    model: DeepEvalBaseLLM = None,
):
    """
    Runs the Langchain and deepeval pipeline on a file or evaluates answers retrieved from the database using relevancy metrics.

    Args:
        response_id (str, optional): The hash ID of the file to query. Required if `use_database` is True.
        key_name (str, optional): The key name to use for the query. Required if `use_database` is True.
        table_name (str, optional): The name of the DynamoDB table. Required if `use_database` is True.
        threshold (float, optional): Minimum relevancy score to pass. Defaults to 0.7.
        model_text (bool, optional): Flag to include model text in the output. Defaults to True.
        exact_text (bool, optional): Flag to include exact quoted text in the output. Defaults to False.
        model (DeepEvalBaseLLM, optional): The LLM model to use for evaluation. If None, a default model is used.

    Returns:
        list: Detailed evaluation results.
    """

    if model is None:
        model = DeepEvalAzureOpenAI()

    # Retrieve formatted_data: a list of questions and associated answers
    formatted_data = get_question_answers(
        response_id=response_id,
        key_name=key_name,
        table_name=table_name,
        model_text=model_text,
        exact_text=exact_text,
    )

    # Create test cases
    test_cases = relevancy_test_cases(formatted_data)

    # Evaluate the relevancy of the answers using DeepEval
    detailed_results = evaluate_answer_relevancy(test_cases, model, threshold=threshold)

    return detailed_results
