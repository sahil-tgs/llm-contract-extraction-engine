from dotenv import load_dotenv
import os
load_dotenv()

# Azure OpenAI setup
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION")
AZURE_API_BASE = os.getenv("AZURE_API_BASE")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")

from openai import AzureOpenAI

az_client = AzureOpenAI(
  api_key=AZURE_API_KEY,
  azure_endpoint=AZURE_API_BASE,
  api_version=AZURE_API_VERSION
)

from docling.document_converter import DocumentConverter

source = "./sample_contract.pdf"  # document per local path or URL
converter = DocumentConverter()
result = converter.convert(source)

# print(result.document.export_to_markdown()) 

PROMPT = """Extract the following fields from the contract and give them as output in json:
- Contract ID
- Contract Name
- Status
- Currency
- Customer ID
- Customer Name
- Contract Start Date
- Contract End Date
- Payment Terms (e.g., 'Net 30')
- Contract Amount
- Metadata: Billing Frequency and Contract Type.

For contracts with missing payment terms, adjust the prompt to prioritize finding contextual clues for default values.
"""

PROMPT1 = """Extract the following fields from the contract in a structured format, ensuring accuracy and handling missing or incomplete data gracefully:

Contract ID: Extract the unique identifier for the contract.
Contract Name: Provide the name of the contract.
Status: Indicate the current status
Currency: Specify the currency code
Customer ID: Extract the unique identifier for the customer
Customer Name: Provide the full name of the customer.
Contract Start Date:
Contract End Date:
Payment Terms: Extract payment terms (e.g., "Net 30"). If missing, infer default values based on contextual clues (e.g., industry standards or other contract details).
Contract Amount: Include both numeric value and currency (e.g., "25000.00 USD").
Metadata: Extract the following subfields:
Billing Frequency: Indicate the billing cycle (e.g., "Monthly," "Quarterly").
Contract Type: Specify the type of contract (e.g., "Subscription").
Additional Instructions:

For any missing field, explicitly state its absence in the extracted output.
Prioritize identifying contextual information or implied terms for missing fields, particularly for Payment Terms and Contract Amount.
Maintain consistent formatting and ensure the extracted data is ready for further automated processing.
"""

result=result.document.export_to_markdown()

output = az_client.chat.completions.create(
    model="ak-gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": PROMPT
        },
        {
            "role": "user",
            "content": result
        }
    ]
)

answer =output.choices[0].message.content

import markdown2
from rich.console import Console
from rich.markdown import Markdown

def print_pretty_markdown(markdown_text: str):
    # Convert markdown to HTML (if needed) or process raw markdown
    html_content = markdown2.markdown(markdown_text)

    # Create a Console object to display rich output
    console = Console()

    # Use the Markdown class from the rich library to format and print markdown
    md = Markdown(markdown_text)

    # Print the formatted markdown
    console.print(md)

# Example usage
markdown_content = answer
print_pretty_markdown(markdown_content)

import re
import pandas as pd
import json

# Input text
text = answer
# Step 1: Extract the JSON portion of the string
start = text.find("{")
end = text.rfind("}") + 1  # Include the closing brace
json_text = text[start:end]

# Step 2: Parse the extracted JSON
data = json.loads(json_text)

# Output: Pretty print the JSON
print(json.dumps(data, indent=4))

# Convert to JSON
json_data = json.dumps(data, indent=4)

import re
import json
from datetime import datetime

# Sample extracted data
extracted_data = json.loads(json_data)

# Define validation functions
def validate_date(date_str):
    """Validate and reformat dates to YYYY-MM-DD."""
    try:
        # Attempt to parse the date
        reformatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        return reformatted_date, True
    except ValueError:
        return None, False  # Invalid date format

def validate_monetary(value):
    """Validate and reformat monetary values to decimals."""
    # Match values like $25,000 or 25000.00
    clean_value = value.replace(",", "")
    match = re.match(r"^\$?([\d,]+(\.\d{2})?)$", clean_value)
    if match:
        # Remove commas, ensure decimal format
        numeric_value = float(match.group(1).replace(",", ""))
        return f"{numeric_value:.2f}", True
    return None, False

def validate_status(status_value):
    """Validate that the status is within the allowed set."""
    valid_statuses = {"draft", "active", "paused", "expired", "disputed"}
    if status_value.lower() in valid_statuses:
        return status_value.capitalize(), True  # Return a standardized format
    return None, False

def handle_missing_or_ambiguous(field, value, default=None):
    """Flag missing/ambiguous data and return defaults if non-critical."""
    if value.lower() in {"(not specified)", "not specified", "(unknown)", "unknown"}:
        return default, False  # Ambiguous or missing data
    return value, True

# Validate each field
validated_data = {}
validation_log = []

for field, value in extracted_data.items():
    if field in {"Contract Start Date", "Contract End Date"}:
        validated_value, is_valid = validate_date(value)
        if not is_valid:
            validation_log.append(f"Invalid date in field '{field}': '{value}'")
    elif field == "Contract Amount":
        validated_value, is_valid = validate_monetary(value)
        if not is_valid:
            validation_log.append(f"Invalid monetary value in field '{field}': '{value}'")
    elif field == "Status":
        validated_value, is_valid = validate_status(value)
        if not is_valid:
            validation_log.append(f"Invalid status in field '{field}': '{value}'")
    elif field in {"Contract ID", "Customer ID"}:
        validated_value, is_valid = handle_missing_or_ambiguous(field, value, default="N/A")
        if not is_valid:
            validation_log.append(f"Missing data in field '{field}': '{value}'")
    else:
        validated_value, is_valid = value, True  # No special validation needed

    # Update validated data
    validated_data[field] = validated_value

# Process nested Metadata
if "Metadata" in extracted_data:
    validated_data["Metadata"] = {}
    for sub_field, sub_value in extracted_data["Metadata"].items():
        validated_data["Metadata"][sub_field], is_valid = handle_missing_or_ambiguous(
            sub_field, sub_value
        )
        if not is_valid:
            validation_log.append(f"Ambiguous data in Metadata field '{sub_field}': '{sub_value}'")

# Output validated data and logs
print("Validated Data:")
print(json.dumps(validated_data, indent=4))

print("\nValidation Log:")
for log in validation_log:
    print(log)

result = f"""
Validated Data:
{json.dumps(json_data, indent=4)}

Validation Log:
{json.dumps(validation_log, indent=4)}
"""

VALID_PROMPT="""
You are a data transformation expert tasked with correcting invalid fields in extracted contract data. Your goal is to process the validated data and validation log, identify fields marked as invalid, and transform them into the proper format. Use the following rules to correct each field type:

Rules for Data Transformation:
Dates:

Ensure all dates are in the YYYY-MM-DD format.
Try to correct the field on the basis of contextual information in () if available.
And Ensure that after updating or retaining the field on the basis of contextual information in (), remove the () and its data from corrected field.
If a valid transformation is not possible, set the date to same as start date (or a provided default).
Monetary Values:

Ensure monetary values are formatted as decimals with two places (e.g., 25000.00).
Remove any non-numeric characters (e.g., $, ,) and properly format the value.
If the value cannot be determined, set it to 0.00.
Missing Fields:

For fields flagged as "missing" or "not specified," use the following defaults:
Contract ID: UNKNOWN_CONTRACT_ID
Customer ID: UNKNOWN_CUSTOMER_ID
If another field is ambiguous or missing, provide a best-effort transformation or leave it as "N/A."
Metadata:

Ensure all nested metadata fields are properly formatted and not ambiguous.
Use default values or corrections where necessary.
Behavior Guidelines:
Be transparent in the transformations you apply. Log the changes you make to the data and explain your reasoning.
Do not modify fields that are already valid.
Return the fully corrected data in the same structure as the input.
Input Format:
You will receive two inputs:

Validated Data: A dictionary containing the data extracted from the contract, with potential invalid fields.
Validation Log: A list of logs specifying fields that are invalid, ambiguous, or missing.
Output Format:
Return a single JSON object with:

Corrected Data: The fully corrected version of the validated data.
Correction Log: A list explaining how each invalid field was corrected or why it was left as-is.

"""

valid_output = az_client.chat.completions.create(
    model="ak-gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": VALID_PROMPT
        },
        {
            "role": "user",
            "content": result
        }
    ]
)
print(valid_output.choices[0].message.content)

# json_data

corrected = valid_output.choices[0].message.content

json_match = re.search(r"```json\n(.*)\n```", corrected, re.S)
if json_match:
    json_data_str = json_match.group(1)  # Extract json string
    try:
        # Parse the json string into a Python dictionary
        extracted_data = json.loads(json_data_str)
        print("Extracted JSON:")
        print(json.dumps(extracted_data, indent=4))
    except json.JSONDecodeError as e:
        print("Failed to parse JSON:", e)
else:
    print("No JSON found in the response.")

import requests
import json

# Validated data (use the output of your validation script)
validated_data = extracted_data
# Map validated data to the API's expected payload structure
payload = {
     "name": validated_data.get("Contract Name", "string"),
    "description": validated_data.get("Description", "string"),
    "status": validated_data.get("Status", "string").lower(),
    "currency": validated_data.get("Contract Name", "string"),
    "start_date":validated_data.get("Contract Start Date", "2024-12-06T14:24:48.532Z"),
    "end_date": validated_data.get("Contract End Date", "2024-12-06T14:24:48.532Z"),
    "customer_id": validated_data.get("Customer ID", "2024-12-06T14:24:48.532Z"),
    "anchor_date": validated_data.get("Anchor Date", "string"),
    "plan_id": validated_data.get("Plan ID", "string")

}

# API details
url = "https://api.zenskar.com/contract_v2"
headers = {
    "accept": "application/json",
    "content-type": "application/json"
}

# Make the POST request
response = requests.post(url, json=payload, headers=headers)

# Output the response
if response.status_code == 200:
    print("Contract successfully created.")
else:
    print(f"Failed to create contract: {response.status_code}")
    print("Response:", response.text)
