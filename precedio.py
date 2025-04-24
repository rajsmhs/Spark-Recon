import yaml
import pandas as pd
import numpy as np
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngine
import spacy
import re
from typing import List
import requests

def load_config(config_path: str) -> dict:
    """Load YAML configuration file"""
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def initialize_presidio():
    """Initialize Presidio analyzer with spaCy model"""
    nlp = spacy.load("en_core_web_lg")
    nlp_engine = NlpEngine(nlp_engine=nlp)
    return AnalyzerEngine(nlp_engine=nlp_engine)

def validate_luhn(card_number: str) -> bool:
    """Implement Luhn algorithm for credit card validation"""
    def digits_of(n): return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d*2))
    return checksum % 10 == 0

def validate_credit_card(number: str, config: dict) -> bool:
    """Validate credit card number based on configuration rules"""
    # Remove spaces and hyphens between digits
    number = re.sub(r'(\d)\s*-\s*(?=\d)', r'\1', number)
    number = re.sub(r'(\d)\s+(?=\d)', r'\1', number)
    
    # Check length requirements
    if not (config['validation']['credit_card']['min_length'] <= 
            len(number) <= config['validation']['credit_card']['max_length']):
        return False
    
    # Validate using Luhn algorithm
    if not validate_luhn(number):
        return False
    
    # BIN validation if enabled
    if config['validation'].get('enforce_bin_check', False):
        bin_number = number[:6]
        bin_api = config['validation']['bin_api']
        try:
            response = requests.get(f"{bin_api}{bin_number}")
            if response.status_code != 200:
                return False
        except:
            return False
    
    return True

def process_chunk(chunk: pd.DataFrame, analyzer: AnalyzerEngine, config: dict) -> List[dict]:
    """Process a chunk of data to detect PII"""
    results = []
    
    for _, row in chunk.iterrows():
        text = ' '.join(str(value) for value in row)
        analyzer_results = analyzer.analyze(
            text=text,
            entities=config['detection']['enabled_entities'],
            language='en'
        )
        
        pii_found = {}
        for result in analyzer_results:
            entity_type = result.entity_type
            value = text[result.start:result.end]
            
            # Validate credit cards
            if entity_type == "CREDIT_CARD":
                if validate_credit_card(value, config):
                    pii_found[entity_type] = value
            else:
                pii_found[entity_type] = value
                
        results.append(pii_found)
    
    return results

def main():
    # Load configuration
    config = load_config('config.yaml')
    
    # Initialize Presidio analyzer
    analyzer = initialize_presidio()
    
    # Read CSV file in chunks
    chunk_size = 100
    results = []
    
    for chunk in pd.read_csv(config['input']['parquet_file'], chunksize=chunk_size):
        chunk_results = process_chunk(chunk, analyzer, config)
        results.extend(chunk_results)
        
    # Convert results to DataFrame and save
    df_results = pd.DataFrame(results)
    df_results.to_parquet(config['output']['duckdb_file'])
    
    # Print results to console
    print("PII Detection Results:")
    print(df_results.to_string())

if __name__ == "__main__":
    main()





import re

# --- Luhn check for credit card ---
def luhn_checksum(card_number):
    def digits_of(n): return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0

# --- Clean text & extract all number sequences ---
def extract_and_classify(text):
    cleaned_text = text.replace('"', '')
    
    # Find digit sequences (with optional spaces or dashes)
    number_patterns = re.findall(r'[\d\s\-]{6,25}', cleaned_text)
    
    for pattern in number_patterns:
        number = re.sub(r'[\s\-]', '', pattern)

        if not number.isdigit():
            continue

        length = len(number)

        # Classify based on length and checks
        if 12 <= length <= 23 and luhn_checksum(number):
            label = "Credit Card"
        elif length == 10:
            label = "Phone Number"
        elif 6 <= length <= 10:
            label = "Account Number"
        else:
            label = "Unknown"

        print(f"Found: {number} → {label}")

# --- Example usage ---
raw_text = '''
Here is some sample data: "4111 1111-1111-1111", 9876543210, and 123-456-7890123.
Account number is "123-456" and extra value is "112233445566".
'''

extract_and_classify(raw_text)












import spacy
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

# 1. Create custom NLP Engine with spaCy
class SpacyNlpEngine:
    def __init__(self, model_name="en_core_web_lg"):
        self.nlp = spacy.load(model_name)

    def process_text(self, text):
        return self.nlp(text)

    def get_entities(self, text):
        doc = self.process_text(text)
        entities = []
        for ent in doc.ents:
            entities.append((ent.text, ent.label_, ent.start_char, ent.end_char))
        return entities

# 2. Set up the Presidio Analyzer with spaCy
def setup_presidio_analyzer():
    spacy_nlp_engine = SpacyNlpEngine()
    nlp_engine_provider = NlpEngineProvider(nlp_engine=spacy_nlp_engine)
    registry = RecognizerRegistry()
    analyzer = AnalyzerEngine(nlp_engine_provider=nlp_engine_provider,
                              registry=registry)
    return analyzer

# 3. Function to identify sensitive information
def identify_sensitive_info(text):
    analyzer = setup_presidio_analyzer()
    
    # Define the entities we want to detect
    entities_to_detect = [
        "CREDIT_CARD",
        "PHONE_NUMBER",
        "PERSON",
        "US_BANK_NUMBER"  # This is the closest match for account number
    ]
    
    # Analyze the text
    results = analyzer.analyze(text=text, entities=entities_to_detect, language='en')
    
    # Organize results
    findings = {entity: [] for entity in entities_to_detect}
    for result in results:
        findings[result.entity_type].append({
            'text': text[result.start:result.end],
            'start': result.start,
            'end': result.end,
            'score': result.score
        })
    
    return findings

# 4. Main function to process text
def process_text(raw_text):
    print("Processing text to identify sensitive information...")
    results = identify_sensitive_info(raw_text)
    
    print("\nFindings:")
    for entity_type, entities in results.items():
        print(f"\n{entity_type}:")
        for entity in entities:
            # Mask sensitive information for display
            masked_text = '*' * (len(entity['text']) - 4) + entity['text'][-4:]
            print(f"  - {masked_text} (confidence: {entity['score']:.2f})")

# 5. Example usage
if __name__ == "__main__":
    sample_text = """
    John Doe's credit card number is 4532-7153-3790-4421.
    His phone number is (555) 123-4567 and his account number is 1234567890.
    Jane Smith can be reached at 987-654-3210.
    The company's main account is 9876543210.
    """
    
    process_text(sample_text)















def preprocess_text(raw_text):
    """
    Preprocess raw text:
    1. Find numbers with 16-23 digits (including spaces and dashes)
    2. Ensure space before such numbers
    3. Remove spaces and dashes between digits
    4. Return cleaned text and extracted numbers
    """
    # Store original positions and numbers
    number_mapping = []
    
    def replace_number_with_clean(match):
        original = match.group(0)
        # Remove spaces and dashes between digits
        cleaned = re.sub(r'[\s-]', '', original)
        if 16 <= len(cleaned) <= 23:
            number_mapping.append(cleaned)
            # Ensure space before number if not at start of line
            return f" {cleaned}"
        return original

    # Pattern for numbers with 16-23 digits (including spaces/dashes)
    pattern = r'(?<!\d)([\d\s-]{16,35})(?!\d)'
    
    # First pass: clean numbers and ensure spaces before them
    cleaned_text = re.sub(pattern, replace_number_with_clean, raw_text)
    
    return cleaned_text, number_mapping
