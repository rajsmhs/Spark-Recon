import re
import yaml
import pandas as pd
import logging
from typing import List, Dict, Tuple
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from tqdm import tqdm
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def preprocess_text(raw_text: str) -> Tuple[str, List[str]]:
    """
    Preprocess the raw text and extract all digit sequences.
    """
    try:
        if pd.isna(raw_text):
            return "", []
        
        text = str(raw_text)  # Convert to string in case of numeric values
        
        # Remove double quotes
        text = text.replace('"', '')
        
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
        
    except Exception as e:
        logger.error(f"Error in preprocess_text: {str(e)}, Text: {raw_text}")
        return "", []

def process_chunk(chunk: pd.DataFrame, analyzer: AnalyzerEngine, 
                 anonymizer: AnonymizerEngine, config: Dict, 
                 bin_table: Dict) -> pd.DataFrame:
    """
    Process a chunk of the DataFrame
    """
    try:
        # Create new columns for results
        chunk['cleaned_text'] = ""
        chunk['digit_sequences'] = None
        chunk['credit_cards'] = None
        chunk['other_pii'] = None
        
        # Process each row in the chunk
        for idx, row in chunk.iterrows():
            try:
                cleaned_text, digit_sequences = preprocess_text(row['statement_details'])
                chunk.at[idx, 'cleaned_text'] = cleaned_text
                chunk.at[idx, 'digit_sequences'] = digit_sequences
                
                # Extract credit cards from digit sequences
                credit_cards = [num for num in digit_sequences 
                              if len(num) >= 12 and is_valid_credit_card(num, bin_table)]
                chunk.at[idx, 'credit_cards'] = credit_cards
                
                # Extract other PII
                if cleaned_text:
                    results = analyzer.analyze(text=cleaned_text, language='en')
                    other_pii = []
                    for result in results:
                        if (result.entity_type in config['pii_types'] or 
                            result.entity_type in config.get('custom_patterns', {})):
                            if result.entity_type != 'CREDIT_CARD':
                                info = {field: getattr(result, field) 
                                      for field in config['output_fields']}
                                other_pii.append(info)
                    chunk.at[idx, 'other_pii'] = other_pii
                    
            except Exception as e:
                logger.error(f"Error processing row {idx}: {str(e)}")
                continue
                
        return chunk
        
    except Exception as e:
        logger.error(f"Error in process_chunk: {str(e)}")
        return pd.DataFrame()

def main():
    try:
        # Load configuration
        with open("config.yaml", "r") as config_file:
            config = yaml.safe_load(config_file)
        
        # Initialize processors
        analyzer = AnalyzerEngine()
        anonymizer = AnonymizerEngine()
        bin_table = load_bin_lookup_table()
        
        # File paths
        input_file = "input.csv"  # Replace with your input file path
        output_file = "output_processed.csv"
        
        # Validate input file
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        logger.info(f"Starting processing of file: {input_file}")
        
        # Read and process the CSV in chunks
        chunk_size = 1000  # Adjust based on your memory constraints
        chunks = []
        
        # Get total number of chunks for progress bar
        total_rows = sum(1 for _ in open(input_file)) - 1  # subtract header
        total_chunks = (total_rows // chunk_size) + 1
        
        with tqdm(total=total_chunks, desc="Processing chunks") as pbar:
            for chunk in pd.read_csv(input_file, chunksize=chunk_size):
                if 'statement_details' not in chunk.columns:
                    raise ValueError("Column 'statement_details' not found in CSV")
                
                processed_chunk = process_chunk(chunk, analyzer, anonymizer, 
                                             config, bin_table)
                chunks.append(processed_chunk)
                pbar.update(1)
        
        # Combine all chunks
        logger.info("Combining processed chunks...")
        final_df = pd.concat(chunks, ignore_index=True)
        
        # Save results
        logger.info(f"Saving results to {output_file}")
        final_df.to_csv(output_file, index=False)
        
        # Print summary
        logger.info("Processing complete. Summary:")
        logger.info(f"Total rows processed: {len(final_df)}")
        logger.info(f"Rows with credit cards: {len(final_df[final_df['credit_cards'].str.len() > 0])}")
        logger.info(f"Rows with other PII: {len(final_df[final_df['other_pii'].str.len() > 0])}")
        
        # Optional: Save summary statistics
        summary_stats = {
            'total_rows': len(final_df),
            'rows_with_credit_cards': len(final_df[final_df['credit_cards'].str.len() > 0]),
            'rows_with_other_pii': len(final_df[final_df['other_pii'].str.len() > 0])
        }
        
        pd.DataFrame([summary_stats]).to_csv('processing_summary.csv', index=False)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()







pii_types:
  - CREDIT_CARD
  - PHONE_NUMBER
  - IBAN
  - AU_ABN
  - AU_ACN
  - AU_TFN
  - AU_MEDICARE

custom_patterns:
  BSB:
    regex: '\b\d{3}-\d{3}\b'
    score: 0.85

output_fields:
  - entity_type
  - start
  - end
  - text
  - score

processing:
  chunk_size: 1000
  max_retries: 3
  timeout: 300





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
