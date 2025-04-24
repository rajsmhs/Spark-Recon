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
