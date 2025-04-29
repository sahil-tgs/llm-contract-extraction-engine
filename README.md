# Single Prompt Strategy: A Cost-Effective Approach
Here's why this approach is technically sound:

## API Economy

- Reduced number of API calls results in lower operational costs
- Minimizes latency by avoiding multiple round-trips
- Better resource utilization through batch processing


## Consistency Management
```
Single Prompt → Single Context → Consistent Output Pattern
vs.
Multiple Prompts → Multiple Contexts → Potential Inconsistencies
```
# Dual Prompt Testing Framework
The implementation of two prompts (concise vs. detailed) serves as an excellent empirical test bed:
## Concise Prompt

### Advantages:

- Higher output consistency
- Reduced token consumption
- More predictable response patterns



### Detailed Prompt

Considerations:

- Enhanced contextual understanding
- Greater extraction precision potential
- Requires structured output control



### Technical Enhancement Pathway
The path to leverage detailed prompts through the instructor library will be a more better and sound architectural decision:
```
Detailed Prompt + Instructor Library
↓
Structured Output Generation
↓
Consistent Response Patterns
↓
Enhanced Extraction Accuracy
```
# Infrastructure Advantages
## DocLing Parser Integration

- Sophisticated handling of complex contract structures
- Pre-processing optimization
- Enhanced text extraction quality
  ![image](https://github.com/user-attachments/assets/c07b760f-e4a2-46fc-af02-3b3d2a4da0d9)


## Azure OpenAI Tool Calling

- Native integration capabilities
- Robust validation framework
- Enhanced error handling

  ![image](https://github.com/user-attachments/assets/c8820dbc-acb8-40e0-bb26-364e999d00ee)

# Future Architecture: Multi-Agent Framework
Proposed enhancement through multi-agent architecture:
## Agent Network Architecture:

![image](https://github.com/user-attachments/assets/434d70fe-1383-44c2-aa7f-3b8b5230a638)


## Key Advantages:

- In-context memory persistence
- Iterative accuracy improvement
- Self-optimizing extraction patterns

## Implementation Benefits Summary

### Cost Optimization

- Reduced API calls
- Efficient token utilization
- Streamlined processing pipeline


### Technical Robustness

- Consistent output patterns
- Enhanced error handling
- Scalable architecture

This implementation demonstrates a sophisticated understanding of LLM architecture constraints while maintaining a clear path for future enhancements through multi-agent systems and memory context integration.


# Detailed Current workflow

## Initial Setup and Configuration

- The code starts by loading environment variables using dotenv
- Configures Azure OpenAI API credentials (key, version, base URL, deployment name)
- Sets up the Azure OpenAI client for making API calls
- Defines validation tools that will help check and format different types of data


# Document Processing

- Takes a PDF file (sample_contract.pdf) as input
- Uses DocumentConverter to convert the PDF into markdown format
- This makes the contract text easier to process


# Information Extraction (First Phase)

- Use one of the two prompts (PROMPT and PROMPT1) to guide the extraction
- PROMPT is concise and focuses on key fields
- PROMPT1 is more detailed with specific instructions for handling missing data
- ## Makes an API call to Azure OpenAI to extract information like:

- Contract ID
- Contract Name
- Status
- Currency
- Customer details
- Dates
- Payment terms
- Contract amount
- Metadata




# Initial Output Processing

- Takes the extracted information and formats it
- Uses pretty printing for markdown content
- Converts the response into JSON format
- Pretty prints the JSON for readability


# Validation Process (Tool-based Validation)

- Goes through each extracted field
- For each field, uses specific validation tools based on field type:

- Dates are checked for correct format (YYYY-MM-DD)
- Monetary values are checked for proper number format
- Status fields are checked against valid options
- IDs are checked for presence and format


- Creates a validation log recording any issues found
- Handles metadata fields separately with their own validation


# LLM-based Validation and Correction

- Takes the validation results and logs
- Uses a specific prompt (VALID_PROMPT) to guide the correction process
## The prompt includes rules for:

- Date formatting
- Monetary value standardization
- Handling missing fields
- Metadata validation
- Makes another API call to Azure OpenAI to get corrected data


# Final Processing

- Extracts the corrected JSON from the LLM response
- Formats and validates the final data
- Prepares the data for API submission


# API Submission

- Prepares a payload with the corrected and validated data
- Includes all required fields for the Zenskar API
- Makes a POST request to the API
- Handles the API response:



Installation
1. Clone the repository:
```
git clone https://github.com/abhinavxanand/assignment.git

```
2. Create and activate virtual environment:

```
python -m venv venv
```
For Linux:
```
source venv/bin/activate
```
For Windows:
```
source venv\Scripts\activate

```
3. Install Requirements:
```
pip install -r requirements.txt

```
4. Run
```
# Without Tool Calling
python main.py
# With Tool Calling
python main_withTool.py
```

