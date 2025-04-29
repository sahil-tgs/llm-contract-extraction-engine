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

# Tool definitions for validation
tools = [
    {
        "type": "function",
        "function": {
            "name": "validate_field",
            "description": "Validate and format contract field values",
            "parameters": {
                "type": "object",
                "properties": {
                    "field_name": {
                        "type": "string",
                        "description": "Name of the field to validate"
                    },
                    "field_value": {
                        "type": "string",
                        "description": "Value to validate"
                    },
                    "field_type": {
                        "type": "string",
                        "enum": ["date", "monetary", "status", "id", "general"],
                        "description": "Type of validation to perform"
                    }
                },
                "required": ["field_name", "field_value", "field_type"]
            }
        }
    }
]

from docling.document_converter import DocumentConverter

source = "./sample_contract.pdf"
converter = DocumentConverter()
result = converter.convert(source)

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
** Incase you are using contextual clue to fill the field then mention it inside the ().
For any missing field, explicitly state its absence in the extracted output.
Prioritize identifying contextual information or implied terms for missing fields, particularly for Payment Terms and Contract Amount.
Maintain consistent formatting and ensure the extracted data is ready for further automated processing.
"""

result = result.document.export_to_markdown()

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

answer = output.choices[0].message.content

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

# Initial validation using tool calling
validation_results = []
validation_log = []

for field, value in data.items():
    if field == "Metadata":
        for sub_field, sub_value in value.items():
            tool_call = az_client.chat.completions.create(
                model="ak-gpt-4o-mini",
                messages=[{"role": "user", "content": f"Validate {sub_field}: {sub_value}"}],
                tools=tools
            )
            if tool_call.choices[0].message.tool_calls:
                result = json.loads(tool_call.choices[0].message.tool_calls[0].function.arguments)
                validation_results.append(result)
                if "error" in result:
                    validation_log.append(f"Metadata.{sub_field}: {result['error']}")
    else:
        field_type = "date" if "Date" in field else \
                    "monetary" if "Amount" in field else \
                    "status" if field == "Status" else \
                    "id" if "ID" in field else "general"
        
        tool_call = az_client.chat.completions.create(
            model="ak-gpt-4o-mini",
            messages=[{"role": "user", "content": f"Validate {field}: {value}"}],
            tools=tools
        )
        if tool_call.choices[0].message.tool_calls:
            result = json.loads(tool_call.choices[0].message.tool_calls[0].function.arguments)
            validation_results.append(result)
            if "error" in result:
                validation_log.append(f"{field}: {result['error']}")

# Prepare validation result for LLM
validation_input = {
    "extracted_data": data,
    "validation_log": validation_log
}

VALID_PROMPT = """
You are a data transformation expert tasked with correcting invalid fields in extracted contract data. Your goal is to process the validated data and validation log, identify fields marked as invalid, and transform them into the proper format. Use the following rules:

Rules for Data Transformation:
Dates:
- Ensure all dates are in the YYYY-MM-DD format.
- Try to correct the field on the basis of contextual information in () if available.
- And Ensure that after updating or retaining the field on the basis of contextual information in (), remove the () and its data from corrected field.
- If a valid transformation is not possible, set the date to same as start date (or a provided default).

Monetary Values:
- Ensure monetary values are formatted as decimals with two places (e.g., 25000.00).
- Remove any non-numeric characters (e.g., $, ,) and properly format the value.
- If the value cannot be determined, set it to 0.00.

Missing Fields:
- For fields flagged as "missing" or "not specified," use the following defaults:
  Contract ID: UNKNOWN_CONTRACT_ID
  Customer ID: UNKNOWN_CUSTOMER_ID
- If another field is ambiguous or missing, provide a best-effort transformation or leave it as "N/A."

Metadata:
- Ensure all nested metadata fields are properly formatted and not ambiguous.
- Use default values or corrections where necessary.

Return the corrected data in JSON format with a correction log.
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
            "content": json.dumps(validation_input)
        }
    ]
)
print(valid_output.choices[0].message.content)

corrected = valid_output.choices[0].message.content

# Extract JSON from corrected output
json_match = re.search(r"```json\n(.*)\n```", corrected, re.S)
if json_match:
    json_data_str = json_match.group(1)
    try:
        extracted_data = json.loads(json_data_str)
        print("Extracted JSON:")
        print(json.dumps(extracted_data, indent=4))
    except json.JSONDecodeError as e:
        print("Failed to parse JSON:", e)
else:
    print("No JSON found in the response.")

import requests

# Prepare API payload
payload = {
    "name": extracted_data.get("Contract Name", "string"),
    "description": extracted_data.get("Description", "string"),
    "status": extracted_data.get("Status", "string").lower(),
    "currency": extracted_data.get("Currency", "string"),
    "start_date": extracted_data.get("Contract Start Date", "2024-12-06T14:24:48.532Z"),
    "end_date": extracted_data.get("Contract End Date", "2024-12-06T14:24:48.532Z"),
    "customer_id": extracted_data.get("Customer ID", "string"),
    "anchor_date": extracted_data.get("Anchor Date", "string"),
    "plan_id": extracted_data.get("Plan ID", "string")
}

# API call
url = "https://api.zenskar.com/contract_v2"
headers = {
    "accept": "application/json",
    "content-type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

if response.status_code == 200:
    print("Contract successfully created.")
else:
    print(f"Failed to create contract: {response.status_code}")
    print("Response:", response.text)
