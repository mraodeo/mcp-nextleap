import os
import json
import time
from typing import List
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from src.agent.models import PulseReport
from src.agent.prompts import pulse_prompt_template

# Load environment variables
load_dotenv()

# Groq specific limits requested by user
GROQ_MODEL = "openai/gpt-oss-120b"
RPM_LIMIT = 30 # Requests per minute
RPD_LIMIT = 1000 # Requests per day
TPM_LIMIT = 8000 # Tokens per minute
TPD_LIMIT = 200000 # Tokens per day

CHARS_PER_TOKEN = 3 # More conservative estimation
# We leave a larger buffer for prompt/output, keeping requests safely under TPM limit
MAX_CHARS_PER_REQUEST = 12000

def get_llm():
    """Returns the configured ChatGroq instance."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing. Please add it to the .env file.")
        
    return ChatGroq(
        groq_api_key=api_key,
        model_name=GROQ_MODEL,
        temperature=0.2, # Low temperature for analytical consistency
        max_retries=2
    )

def chunk_reviews(reviews: List[dict], max_chars: int = MAX_CHARS_PER_REQUEST) -> List[List[dict]]:
    """
    Splits the reviews into batches where the JSON string representation
    of each batch is under the max_chars limit to prevent hitting the TPM ceiling.
    """
    chunks = []
    current_chunk = []
    current_length = 0
    
    for rev in reviews:
        # Calculate rough character length of the review as a JSON string
        rev_len = len(json.dumps(rev))
        
        if current_length + rev_len > max_chars and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [rev]
            current_length = rev_len
        else:
            current_chunk.append(rev)
            current_length += rev_len
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def analyze_reviews_with_groq(reviews: List[dict]) -> PulseReport:
    """
    Analyzes reviews while respecting Groq's strict 8K TPM limits.
    If the reviews exceed the limit, it chunks them, analyzes each chunk,
    and then does a final pass to combine the results into one PulseReport.
    """
    if not reviews:
        raise ValueError("No reviews provided for analysis.")
        
    llm = get_llm()
    structured_llm = llm.with_structured_output(PulseReport)
    
    chain = pulse_prompt_template | structured_llm
    
    chunks = chunk_reviews(reviews)
    print(f"Divided {len(reviews)} reviews into {len(chunks)} chunks to respect the 8K TPM limits.")
    
    chunk_reports = []
    
    for i, chunk in enumerate(chunks):
        if i > 0:
            print(f"Waiting 60 seconds to reset Groq 8K TPM rate limit bucket...")
            time.sleep(60) 
            
        print(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} reviews)...")
        chunk_json = json.dumps(chunk, indent=2)
        
        report = chain.invoke({"reviews_json": chunk_json})
        chunk_reports.append(report)
        
    # If there was only enough data for 1 chunk, just return it
    if len(chunk_reports) == 1:
        return chunk_reports[0]
        
    # If there are multiple chunks, map-reduce them into a single final report
    print("Combining intermediate chunk reports into a final master Pulse Report...")
    
    # We serialize the intermediate structured reports back to JSON to feed into the final pass
    intermediate_json = json.dumps([r.model_dump() for r in chunk_reports], indent=2)
    
    print(f"Waiting 60 seconds before final combination to respect rate limits...")
    time.sleep(60)
    
    final_report = chain.invoke({"reviews_json": intermediate_json})
    return final_report

def format_pulse_report_to_markdown(report: PulseReport) -> str:
    """
    Formats the structured data into the final, readable Markdown string.
    """
    md = "# Groww App Review Pulse Report\n\n"
    
    md += "## Key Themes\n"
    for theme in report.themes:
        md += f"- {theme}\n"
        
    md += "\n## Verbatim Quotes\n"
    for quote in report.quotes:
        md += f"> \"{quote}\"\n"
        
    md += "\n## Action Ideas\n"
    for action in report.actions:
        md += f"- {action}\n"
        
    return md
