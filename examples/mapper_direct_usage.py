"""
Example: Using Mapper Module Directly (Programmatic)
This shows how to import and call mapper functions directly in Python
"""

import sys
import os
from pathlib import Path

# Add mapper module to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules" / "mapper" / "src"))

# Import mapper components
from orchestrator import PDFAutofiller
from configs.factory import ConfigFactory

def example_direct_usage():
    """Example: Direct programmatic usage of mapper module"""
    
    # 1. Create config (local mode)
    config = ConfigFactory.create_config(source_type="local")
    
    # 2. Initialize the orchestrator
    autofiller = PDFAutofiller(config)
    
    # 3. Define paths
    input_pdf = "data/modules/mapper_sample/input/small_4page.pdf"
    input_json = "data/modules/mapper_sample/form_keys_flat.json"
    
    # 4. Process the PDF
    result = autofiller.process_pdf(
        pdf_path=input_pdf,
        input_json_path=input_json,
        user_id="test_user",
        pdf_doc_id="test_pdf_001"
    )
    
    # 5. Get results
    print(f"✅ Processing complete!")
    print(f"📄 Filled PDF: {result['filled_pdf_path']}")
    print(f"📊 Mapping data: {result['mapping_path']}")
    print(f"🔢 Fields mapped: {len(result.get('mappings', {}))}")
    
    return result


def example_step_by_step():
    """Example: Call individual steps separately"""
    
    from extractors.fitz_extract_lines import FitzExtractor
    from mappers.semantic_mapper import SemanticMapper
    
    # Step 1: Extract fields from PDF
    print("📄 Step 1: Extracting fields...")
    extractor = FitzExtractor()
    extracted_fields = extractor.extract("data/modules/mapper_sample/input/small_4page.pdf")
    print(f"   Found {len(extracted_fields)} fields")
    
    # Step 2: Map fields to input data
    print("🗺️  Step 2: Mapping fields...")
    mapper = SemanticMapper()
    input_data = {"name": "John Doe", "date": "2026-03-10"}
    mappings = mapper.map(extracted_fields, input_data)
    print(f"   Mapped {len(mappings)} fields")
    
    # Step 3: Fill PDF
    print("✍️  Step 3: Filling PDF...")
    #filler = PDFFiller()
    output_path = "output/filled.pdf"
    # filler.fill(
    #     input_pdf="data/modules/mapper_sample/input/small_4page.pdf",
    #     mappings=mappings,
    #     output_path=output_path
    # )
    # print(f"   ✅ Created: {output_path}")
    
    return output_path


def example_with_custom_config():
    """Example: Use custom configuration"""
    
    import configparser
    
    # Load custom config
    config_obj = configparser.ConfigParser()
    config_obj.read("modules/mapper/config.ini")
    
    # Override specific settings
    config_obj.set("general", "source_type", "local")
    config_obj.set("mapping", "llm_model", "gpt-4o")
    config_obj.set("mapping", "llm_temperature", "0.05")
    
    # Create config from custom settings
    config = ConfigFactory.create_config(
        source_type="local",
        config_obj=config_obj
    )
    
    # Use it
    autofiller = PDFAutofiller(config)
    result = autofiller.process_pdf(
        pdf_path="data/modules/mapper_sample/input/small_4page.pdf",
        input_json_path="data/modules/mapper_sample/form_keys_flat.json"
    )
    
    return result


if __name__ == "__main__":
    print("🚀 Mapper Module - Direct Usage Examples\n")
    
    # Example 1: Full orchestration
    print("=" * 60)
    print("Example 1: Full Orchestration")
    print("=" * 60)
    result = example_direct_usage()
    
    print("\n")
    
    # Example 2: Step by step
    print("=" * 60)
    print("Example 2: Step-by-Step Processing")
    print("=" * 60)
    output = example_step_by_step()
    
    print("\n✅ All examples complete!")
