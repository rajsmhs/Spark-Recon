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





import re
import yaml
from typing import List, Dict, Tuple
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

def preprocess_text(raw_text: str) -> Tuple[str, List[str]]:
    """
    Preprocess the raw text and extract all digit sequences.
    
    Returns:
    - Cleaned text
    - List of all digit sequences found in the text
    """
    # Remove double quotes
    text = raw_text.replace('"', '')
    
    # Add space between letters and numbers
    text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
    
    # Remove parentheses
    text = re.sub(r'[\(\)]', '', text)
    
    # Remove hyphens between numbers but preserve hyphens in words
    text = re.sub(r'(\d)-+(\d)', r'\1\2', text)
    
    # Remove spaces between numbers
    text = re.sub(r'(\d)\s+(\d)', r'\1\2', text)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Extract all digit sequences
    digit_sequences = re.findall(r'\d+', text)
    
    return text.strip(), digit_sequences

def load_bin_lookup_table():
    # This function should load a BIN lookup table
    # For this example, we'll use a dummy table
    return {
        '400000': {'issuer': 'Visa', 'length': [13, 16]},
        '510000': {'issuer': 'Mastercard', 'length': [16]},
        # Add more BIN entries as needed
    }

def luhn_algorithm(card_number: str) -> bool:
    digits = [int(d) for d in card_number]
    checksum = 0
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum += sum(odd_digits)
    for d in even_digits:
        checksum += sum(divmod(d * 2, 10))
    return checksum % 10 == 0

def is_valid_credit_card(number: str, bin_table: Dict) -> bool:
    if not 12 <= len(number) <= 23:
        return False
    
    bin_prefix = number[:6]
    if bin_prefix not in bin_table:
        return False
    
    expected_lengths = bin_table[bin_prefix]['length']
    if len(number) not in expected_lengths:
        return False
    
    return luhn_algorithm(number)

def extract_credit_card_numbers(digit_sequences: List[str], bin_table: Dict) -> List[str]:
    valid_cards = [num for num in digit_sequences if len(num) >= 12 and is_valid_credit_card(num, bin_table)]
    return valid_cards

def process_statement(raw_text: str, analyzer: AnalyzerEngine, anonymizer: AnonymizerEngine, config: Dict, bin_table: Dict) -> Dict[str, List]:
    # Preprocess the text
    cleaned_text, digit_sequences = preprocess_text(raw_text)
    
    extracted_info = {
        'credit_cards': extract_credit_card_numbers(digit_sequences, bin_table),
        'other_pii': [],
        'all_digit_sequences': digit_sequences
    }
    
    # Analyze the text for other PII
    results = analyzer.analyze(text=cleaned_text, language='en')
    
    for result in results:
        if result.entity_type in config['pii_types'] or result.entity_type in config.get('custom_patterns', {}):
            if result.entity_type != 'CREDIT_CARD':  # We've already handled credit cards
                info = {field: getattr(result, field) for field in config['output_fields']}
                extracted_info['other_pii'].append(info)
    
    return extracted_info

def main():
    # Load configuration
    with open("config.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)
    
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
    bin_table = load_bin_lookup_table()
    
    # Example statement details with various formatting
    test_cases = [
        'Customer payment via card "4111-1111-1111-1111"',
        'Trans ID(4111 1111 1111 1111)payment',
        'Payment4111111111111111received',
        'Card num: 4111-1111-1111-1111',
        'BSB: (062-000), Account: "12345678"'
    ]
    
    for test_case in test_cases:
        print("\nOriginal text:", test_case)
        cleaned_text, digit_sequences = preprocess_text(test_case)
        print("Preprocessed text:", cleaned_text)
        print("Extracted digit sequences:", digit_sequences)
        
        extracted_info = process_statement(test_case, analyzer, anonymizer, config, bin_table)
        
        print("Extracted Credit Card Numbers:")
        for card in extracted_info['credit_cards']:
            print(card)
        
        print("Other Extracted PII Information:")
        for info in extracted_info['other_pii']:
            print(info)
        
        print("All Digit Sequences:")
        print(extracted_info['all_digit_sequences'])

if __name__ == "__main__":
    main()










