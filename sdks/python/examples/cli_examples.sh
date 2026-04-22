#!/usr/bin/env python3
"""
CLI Examples for PDF Autofiller

This file demonstrates various CLI usage patterns.
"""

# ============================================================================
# BASIC USAGE
# ============================================================================

# Extract fields from a PDF
# pdf-autofiller extract input.pdf --output extracted.json

# Create embedded PDF (recommended for reuse)
# pdf-autofiller make-embed input.pdf --output embedded.pdf

# Fill the embedded PDF
# pdf-autofiller fill embedded.pdf data.json --output filled.pdf


# ============================================================================
# WITH RAG PREDICTIONS (DUAL MAPPER)
# ============================================================================

# Create embedded PDF with RAG predictions for better accuracy
# pdf-autofiller make-embed input.pdf --use-rag --output embedded.pdf


# ============================================================================
# COMPLETE PIPELINE (ONE COMMAND)
# ============================================================================

# Run everything at once (extract → map → embed → fill)
# pdf-autofiller run-all input.pdf data.json --output filled.pdf


# ============================================================================
# CUSTOM API ENDPOINT
# ============================================================================

# Use custom API endpoint
# pdf-autofiller --api-url https://api.example.com extract input.pdf

# With authentication
# pdf-autofiller --api-url https://api.example.com --api-key your-key extract input.pdf


# ============================================================================
# SESSION TRACKING
# ============================================================================

# Track operations with session ID
# pdf-autofiller --session-id session-123 extract input.pdf


# ============================================================================
# CHECK OPERATIONS
# ============================================================================

# Check if PDF has embedded metadata
# pdf-autofiller check-embed input.pdf


# ============================================================================
# BATCH PROCESSING (Bash Script)
# ============================================================================

# Process multiple PDFs
"""
#!/bin/bash

for pdf in *.pdf; do
    echo "Processing $pdf..."
    pdf-autofiller make-embed "$pdf" --use-rag
done
"""


# ============================================================================
# WITH ENVIRONMENT VARIABLES
# ============================================================================

# Set environment variables
"""
export PDF_AUTOFILLER_API_URL="https://api.example.com"
export PDF_AUTOFILLER_API_KEY="your-api-key"

# Now commands use these by default
pdf-autofiller extract input.pdf
"""


# ============================================================================
# PIPELINE WITH INTERMEDIATE FILES
# ============================================================================

# Step 1: Extract
# pdf-autofiller extract input.pdf --output extracted.json

# Step 2: Map (with specific mapper type)
# pdf-autofiller map input.pdf data.json --mapper-type ensemble --output mapping.json

# Step 3: Embed
# pdf-autofiller embed input.pdf mapping.json

# Step 4: Fill
# pdf-autofiller fill embedded.pdf data.json --output filled.pdf


# ============================================================================
# ERROR HANDLING
# ============================================================================

# The CLI provides rich error messages and status indicators
# Try these to see error handling:

# Missing file
# pdf-autofiller extract nonexistent.pdf

# Invalid API endpoint
# pdf-autofiller --api-url https://invalid-url.com extract input.pdf


# ============================================================================
# PRETTY OUTPUT
# ============================================================================

# The CLI uses Rich library for beautiful terminal output:
# - ✅ Success indicators
# - ⏱️ Execution time
# - 🎯 Cache hit/miss status
# - 📊 Mapper information
# - 📤 Output file paths in tables
# - Color-coded status messages
