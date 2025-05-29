
<p align="center"><img src="../main/doc/source/_static/main_logo.png" | safe alt="Extr@ct logo" width="600"/></p>



# 🔨 Extr@ct: Consultation Email Extraction Tool 🔨

> [!IMPORTANT]
> This repo is currently work in progress 🔨. The outputs of the application cannot be guaranteed at this time. Use with caution.

## Overview
Public consultations are processes where government bodies invite the public to share their views on policy issues to inform decision-making. This is encouraged via response to specific, structured questions but responses can also be submitted as unstructured text via email.

For all responses to the consultation to be analysed, feedback from unstructured text responses needs to be processed and assigned to the relevant questions in the consultation. This process is currently time-consuming, error-prone and resource-intensive

Extr@ct is a Flask application that uses AI tools to automate the processing of these unstructured consultation responses, enabling faster information extraction and reducing the burden on staff. The tool allows a user to upload a structured list of questions and an unstructured response - the AI will then extract relevant answers.

## Project Status
This project is currently in development and not production-ready. We have prioritised functionality over the user interface for this initial release, so there may be unexpected errors. UI improvements are planned for future releases.

The project requirements are currently specific to the infrastructure within DSIT, including AWS and Azure services for deployment and GPT-4o access. We aim to support flexible model, server, and database configurations in future versions.

We are evaluating performance using historic labelled data and testing on live consultations. Initial results are promising, and we hope to publish a comprehensive evaluation in future.

## Setup
### Prerequisites
Before getting started ensure you have installed:
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
* [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
* [Docker](https://docs.docker.com/engine/install/)
* [Python 3.12](https://www.python.org/downloads/)
* [Poetry](https://python-poetry.org/docs/)
* Create a GPT-4o Endpoint in [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service)

### Create the Infrastructure

The application relies on databases created in AWS and an Azure OpenAI endpoint. The databases required are created using `terraform` and are detailed in the `infrastructure/` folder. 

To get started, log in to AWS with 
```
aws sso login --profile <your_aws_profile>
```
where `<your_aws_profile>` is the name of your AWS profile. If you have not created your AWS profile locally, use the [AWS Documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html#sso-configure-profile-token-auto-sso) to configure your setup.

Create the required databases in AWS using `terraform`
```
cd infrastructure/
terraform init
terraform apply
cd ..
```
and review the changes.

### Configuration
Within the AWS S3 bucket, within the AWS Management Console, created by `terraform` (default: `extract-upload-data-dev`) create the system and human prompt templates in a new folder called `prompt_templates/approved/prompt_template_system.jinja` and `prompt_templates/approved/prompt_template_human.jinja`. You will need to copy these prompt templates from your local repo to the AWS bucket created by terraform. The templates can be found in this directory `prompt_templates/approved/...`

Next, we need to add your GPT-4o model configuration secrets which are handled by AWS Secrets Manager. To add the required secrets go to AWS Management Console > Secrets Manager > Secrets > extract-secrets. From here you can manually insert your secrets as key-value pairs. Please insert the following key-value pairs.
|Key|Explanation|Example|
|---|---|---|
|AZURE_OPENAI_ENDPOINT|Azure OpenAI URI|https://xyz.openai.azure.com/|
|AZURE_OPENAI_API_KEY|API Key for Azure GPT-4o|abcd1234|
|AZURE_OPENAI_API_VERSION|Version of the deployed GPT-4o model|1970-01-01-preview|
|AZURE_OPENAI_CHAT_DEPLOYMENT_NAME|The name of your deployed model|my-gpt-4o-model|

For details on using Secrets Manager see these [docs](https://docs.aws.amazon.com/prescriptive-guidance/latest/secure-sensitive-data-secrets-manager-terraform/using-secrets-manager-and-terraform.html)

### Run the Application
To start developing locally, install dependencies using poetry
```
poetry install
```
and create a `.env` file. If using the default installation instructions as above then use
```.env
MODEL_SECRETS_ID=extract-secrets
RESPONSES_TABLE_NAME=extract-responses
QUESTIONS_TABLE_NAME=extract-questions
REVIEW_TABLE_NAME=extract-reviews
MANUAL_TABLE_NAME=extract-manual-reviews
USER_UPLOAD_S3_BUCKET=extract-upload-data-dev
SYSTEM_PROMPT_TEMPLATE_PATH=prompt_templates/approved/prompt_template_system.jinja
HUMAN_PROMPT_TEMPLATE_PATH=prompt_templates/approved/prompt_template_human.jinja
REGION=eu-west-2
ENVIRONMENT=DEV
```

| Key|Description|
|---|---|
| MODEL_SECRETS_ID| AWS Secrets Manager ID|
| RESPONSES_TABLE_NAME| DynamoDB table name, responses overview data|
| QUESTIONS_TABLE_NAME| DynamoDB table name, each question and model response|
| REVIEW_TABLE_NAME| DynamoDB table name, reviews carried out by the user|
| MANUAL_TABLE_NAME| DynamoDB table name, text manually added to the extraction|
| USER_UPLOAD_S3_BUCKET| S3 bucket name, used to store uploaded questions and responses as well as prompt templates|
| SYSTEM_PROMPT_TEMPLATE_PATH| S3 file path, location of the system prompt template|
| HUMAN_PROMPT_TEMPLATE_PATH| S3 filepath, location of the human prompt template|
| REGION| AWS region services are deployed in|
| ENVIRONMENT| Can be DEV, PREPROD, or PROD|

If you have changed any naming of infrastructure this will need to be reflected in `.env`.

Now SSO into AWS using your AWS profile name
```
aws sso login --profile <your_aws_profile>
```
The Docker container can be built using
```
docker build -t <image_name> .
```
where we define the name of our Docker image build locally here, replacing `<image_name>` with an image name of our choice (e.g., extract)

Then run the image with your AWS credentials, your `.env` file and your AWS profile (named `<your_aws_profile>`)
```
docker run -it \
  -p 5000:5000 \
  --env-file=.env \
  -v ~/.aws/credentials:/root/.aws/credentials:ro \
  -v ~/.aws/config:/root/.aws/config:ro \
  -v ~/.aws/sso/cache:/root/.aws/sso/cache:ro \
  -v ~/.aws/cli/cache:/root/.aws/cli/cache:ro \
  -v $(pwd)/.env:/app/.env:ro \
  -e AWS_PROFILE=<your_aws_profile> \
  <image_name>
```
Ensure you have logged into AWS via SSO to ensure the Docker container can connect to AWS via your AWS credentials.

Go to a browser and `http://127.0.0.1:5000` to see the app running.

## Using the Application
1. Go to "Upload Questions" tab and upload a `.csv` of consultation questions you want to extract responses to from unstructured text. The `.csv` must have `question_label` and `question_text` columns where `question_label` values are unique to each question. 

2. Then go to "Upload Responses" to upload the `.pdf`s you want to extract question responses from. You can upload multiple `.pdf`s at once.

3. Then go to "Extract" and press "Activate LLM Extractor" button. This will start the processing of the questions and responses. Note this can take a few minutes depending on the number of questions and the size of the pdf(s). Once the extraction is complete an "Extraction successful" message will appear if successful or an error message if not.

4. Once extracted, go to "Review" to view all the questions the model has extracted responses to. You will then be able to Accept or Reject the model response. The process will return the exact text that is in the `.pdf`, if you want to review what the model actually returned you can go to "Show Details" or if you want to see the `.pdf` text in full go to "Full Response Text".

5. Then go to "Manual Extraction" to view all questions, including ones the model has extracted nothing for, where you will have the option to manually include any relevant text the model hasn't included to each question.

## Roadmap
Our roadmap includes:
* Deploying on live consultations in the immediate term
* Publishing a robust evaluation of the tool's performance
* Releasing a stable v1.0 once the application reaches maturity

## Licence
This project is licensed under the MIT Licence. See the [LICENCE](LICENCE) file for details.

## Contributing
If you'd like to contribute please follow the [CONTRIBUTING.md](CONTRIBUTING.md) link.
