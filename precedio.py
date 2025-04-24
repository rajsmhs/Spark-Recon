import yaml
import pandas as pd
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from typing import List, Dict
import re

def load_config(yaml_path: str) -> Dict:
    """Load YAML configuration file"""
    with open(yaml_path, 'r') as file:
        return yaml.safe_load(file)

def create_custom_recognizer(entity_name: str, regex_pattern: str, score: float, description: str):
    """Create a custom pattern recognizer"""
    return PatternRecognizer(
        supported_entity=entity_name,
        patterns=[Pattern(regex_pattern, score)],
        context=['bank', 'account', 'bsb'],
        description=description
    )

def setup_analyzer(config: Dict) -> AnalyzerEngine:
    """Setup analyzer with standard and custom entities"""
    analyzer = AnalyzerEngine()
    
    # Add custom recognizers
    if 'custom_entities' in config['detection']:
        for entity_name, entity_config in config['detection']['custom_entities'].items():
            custom_recognizer = create_custom_recognizer(
                entity_name=entity_name,
                regex_pattern=entity_config['regex'],
                score=entity_config['score'],
                description=entity_config['description']
            )
            analyzer.registry.add_recognizer(custom_recognizer)
    
    return analyzer

def analyze_text(text: str, analyzer: AnalyzerEngine, enabled_entities: List[str]) -> List:
    """Analyze text for PII entities"""
    results = analyzer.analyze(
        text=text,
        language='en',
        entities=enabled_entities
    )
    return results

def process_file(config: Dict):
    """Main function to process the input file and detect PII"""
    # Setup analyzer
    analyzer = setup_analyzer(config)
    
    # Get enabled entities
    enabled_entities = config['detection']['enabled_entities']
    
    # Read input file
    input_file = config['input']['parquet_file']
    df = pd.read_parquet(input_file)
    
    # Initialize results storage
    pii_findings = []
    
    # Process each column in the DataFrame
    for column in df.columns:
        # Convert column to string and analyze each value
        for index, value in df[column].astype(str).items():
            resultsHere's a Python function using Presidio to detect PII information based on the provided YAML configuration:

```python
import yaml
import re
import pyarrow.parquet as pq
import duckdb
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, RecognizerRegistry

def detect_pii(config_file, input_file, output_file):
    # Load configuration
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)

    # Initialize Presidio analyzer
    registry = RecognizerRegistry()
    analyzer = AnalyzerEngine(registry=registry)

    # Add custom entities
    for entity, details in config['detection'].get('custom_entities', {}).items():
        custom_recognizer = PatternRecognizer(
            supported_entity=entity,
            patterns=[re.compile(details['regex'])],
            name=entity,
            context=["AU", "Australia"],
            supported_language="en"
        )
        registry.add_recognizer(custom_recognizer)

    # Read input data
    table = pq.read_table(config['input']['parquet_file'])
    df = table.to_pandas()

    # Function to analyze text for PII
    def analyze_text(text):
        results = analyzer.analyze(
            text=str(text),
            language='en',
            entities=config['detection']['enabled_entities'] + list(config['detection'].get('custom_entities', {}).keys())
        )
        return [result.entity_type for result in results]

    # Apply PII detection to each column
    for column in df.columns:
        df[f'{column}_pii'] = df[column].apply(analyze_text)

    # Create DuckDB connection and table
    conn = duckdb.connect(config['output']['duckdb_file'])
    conn.register('df', df)
    conn.execute("CREATE TABLE pii_data AS SELECT * FROM df")
    conn.close()

    print(f"PII detection complete. Results stored in {config['output']['duckdb_file']}")

# Usage
detect_pii('config.yml', './data/data_1.csv', 'pii_data.duckdb')
