# GPU Configuration Examples for PDF Autofillr
# ==============================================
# This file demonstrates different GPU configurations for various deployment scenarios

# ============================================================================
# SCENARIO 1: Local Development - No GPU (CPU Only)
# ============================================================================
# Use Case: Learning, testing, budget laptop
# Expected Performance: 60-300 seconds per PDF
# ============================================================================

[general]
source_type = local

[mapping]
llm_model = ollama/llama3.1    # Small model for CPU
llm_temperature = 0.05

[gpu]
gpu_mode = cpu                  # Force CPU-only
gpu_memory_limit = 0            # Not applicable for CPU
num_gpu_layers = 0              # All layers on CPU
low_vram_mode = false           # Not needed for CPU
gpu_device = 0

# ============================================================================
# SCENARIO 2: Local Development - NVIDIA GPU (8GB VRAM)
# ============================================================================
# Use Case: Development with mid-range NVIDIA GPU (RTX 3060, RTX 4060, etc.)
# Expected Performance: 10-30 seconds per PDF
# Hardware: CUDA-capable NVIDIA GPU with 8GB VRAM
# ============================================================================

[general]
source_type = local

[mapping]
llm_model = ollama/llama3.1    # 7B model fits in 8GB VRAM
llm_temperature = 0.05

[gpu]
gpu_mode = cuda                 # NVIDIA CUDA
gpu_memory_limit = 6000         # 6GB limit (leave 2GB for system)
num_gpu_layers = -1             # All layers on GPU
low_vram_mode = false           # Not needed with 8GB
gpu_device = 0                  # First GPU

# ============================================================================
# SCENARIO 3: Local Development - NVIDIA GPU (Low VRAM, 4-6GB)
# ============================================================================
# Use Case: Development with low-end NVIDIA GPU (GTX 1650, GTX 1660, etc.)
# Expected Performance: 20-50 seconds per PDF
# Hardware: CUDA-capable NVIDIA GPU with 4-6GB VRAM
# ============================================================================

[general]
source_type = local

[mapping]
llm_model = ollama/mistral      # Smaller, more efficient model
llm_temperature = 0.05

[gpu]
gpu_mode = cuda
gpu_memory_limit = 4000         # 4GB limit (for 6GB VRAM)
num_gpu_layers = 25             # Partial GPU offload (not all layers)
low_vram_mode = true            # Enable memory optimization
gpu_device = 0

# ============================================================================
# SCENARIO 4: Local Development - Apple Silicon (M1/M2/M3)
# ============================================================================
# Use Case: Development on Mac with Apple Silicon
# Expected Performance: 10-30 seconds per PDF
# Hardware: Apple M1, M2, or M3
# ============================================================================

[general]
source_type = local

[mapping]
llm_model = ollama/llama3.1
llm_temperature = 0.05

[gpu]
gpu_mode = mps                  # Apple Metal Performance Shaders
gpu_memory_limit = 0            # Unlimited (unified memory)
num_gpu_layers = -1             # All layers on GPU
low_vram_mode = false
gpu_device = 0

# ============================================================================
# SCENARIO 5: High-End Workstation - NVIDIA GPU (24GB VRAM)
# ============================================================================
# Use Case: Production-quality local processing with large models
# Expected Performance: 8-20 seconds per PDF
# Hardware: RTX 4090, RTX A5000, etc.
# ============================================================================

[general]
source_type = local

[mapping]
llm_model = ollama/llama3.1:70b    # Large 70B model for best quality
llm_temperature = 0.05
llm_max_tokens = 8192

[gpu]
gpu_mode = cuda
gpu_memory_limit = 22000        # 22GB (leave 2GB for system)
num_gpu_layers = -1             # All 80 layers on GPU
low_vram_mode = false
gpu_device = 0

# ============================================================================
# SCENARIO 6: Multi-GPU System - 2x NVIDIA GPUs
# ============================================================================
# Use Case: High-throughput processing with multiple GPUs
# Expected Performance: 2x throughput (parallel processing)
# Hardware: 2 or more NVIDIA GPUs
# ============================================================================

[general]
source_type = local

[mapping]
llm_model = ollama/llama3.1
llm_temperature = 0.05

[gpu]
gpu_mode = cuda
gpu_memory_limit = 0            # Let Ollama manage multi-GPU
num_gpu_layers = -1
low_vram_mode = false
gpu_device = -1                 # Use all available GPUs

# Note: To run on specific GPU, create separate instances:
# Instance 1: gpu_device = 0
# Instance 2: gpu_device = 1

# ============================================================================
# SCENARIO 7: Cloud Deployment - AWS Lambda (No GPU)
# ============================================================================
# Use Case: Serverless deployment with cloud LLM
# Expected Performance: 2-5 seconds per PDF
# Cost: ~$0.01-0.03 per PDF
# ============================================================================

[general]
source_type = aws

[mapping]
llm_model = bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
llm_temperature = 0.05

[aws]
cache_registry_path = s3://my-bucket/cache/hash_registry.json
output_base_path = s3://my-bucket/output

[gpu]
gpu_mode = cpu                  # Lambda doesn't support GPU
gpu_memory_limit = 0
num_gpu_layers = 0
low_vram_mode = false
gpu_device = 0

# ============================================================================
# SCENARIO 8: Kubernetes with GPU - Production
# ============================================================================
# Use Case: Scalable production deployment with local LLMs on GPU
# Expected Performance: 10-30 seconds per PDF
# Hardware: Kubernetes cluster with GPU nodes
# ============================================================================

[general]
source_type = aws               # Or azure, gcp

[mapping]
llm_model = ollama/llama3.1
llm_temperature = 0.05

[aws]
cache_registry_path = s3://prod-bucket/cache/hash_registry.json
output_base_path = s3://prod-bucket/output

[gpu]
gpu_mode = cuda                 # Kubernetes GPU node
gpu_memory_limit = 14000        # Share 16GB GPU with overhead
num_gpu_layers = -1
low_vram_mode = false
gpu_device = 0                  # K8s assigns specific GPU

# ============================================================================
# SCENARIO 9: Hybrid - Local Ollama + Cloud Storage
# ============================================================================
# Use Case: Free LLM processing with cloud storage
# Expected Performance: 10-30 seconds per PDF (GPU), $0 LLM cost
# ============================================================================

[general]
source_type = aws               # Store data in cloud

[mapping]
llm_model = ollama/llama3.1    # But use local free LLM

[aws]
cache_registry_path = s3://my-bucket/cache/hash_registry.json
output_base_path = s3://my-bucket/output

[gpu]
gpu_mode = cuda
gpu_memory_limit = 6000
num_gpu_layers = -1
low_vram_mode = false
gpu_device = 0

# ============================================================================
# SCENARIO 10: Docker Container with GPU
# ============================================================================
# Use Case: Containerized deployment with GPU acceleration
# Expected Performance: 10-30 seconds per PDF
# Docker Command: docker run --gpus all -v config.ini:/app/config.ini mapper:latest
# ============================================================================

[general]
source_type = local

[mapping]
llm_model = ollama/llama3.1
llm_temperature = 0.05

[gpu]
gpu_mode = auto                 # Auto-detect GPU in container
gpu_memory_limit = 6000
num_gpu_layers = -1
low_vram_mode = false
gpu_device = 0

# ============================================================================
# GPU CONFIGURATION REFERENCE
# ============================================================================

# gpu_mode options:
#   - auto: Automatically detect CUDA/MPS/CPU (recommended for Docker)
#   - cuda: Force NVIDIA CUDA (requires CUDA toolkit and nvidia-docker)
#   - mps: Force Apple Metal Performance Shaders (M1/M2/M3 Macs)
#   - cpu: Force CPU-only (no GPU acceleration)

# gpu_memory_limit:
#   - 0: Unlimited (use all available VRAM)
#   - <number>: Limit in MB (e.g., 6000 for 6GB)
#   - Recommendation: Leave 2-4GB free for system
#     - 8GB VRAM → set to 6000
#     - 16GB VRAM → set to 14000
#     - 24GB VRAM → set to 22000

# num_gpu_layers:
#   - -1: Offload all layers to GPU (recommended if VRAM allows)
#   - 0: Keep all layers on CPU (cpu-only mode)
#   - <number>: Offload specific number of layers
#     - 7B models: ~35-40 layers
#     - 13B models: ~40-50 layers
#     - 70B models: ~80 layers (needs 48GB+ VRAM)

# low_vram_mode:
#   - false: Normal mode (recommended for 8GB+ VRAM)
#   - true: Memory-optimized mode (slower, uses less VRAM)
#   - Use when: GPU has < 8GB VRAM

# gpu_device:
#   - 0: First GPU
#   - 1: Second GPU
#   - -1: Use all available GPUs (multi-GPU)
#   - For multi-GPU: Ollama will distribute load automatically

# ============================================================================
# PERFORMANCE EXPECTATIONS
# ============================================================================

# Processing Time per PDF Form (approximate):
#
# CPU Only:
#   - 7B model: 60-180 seconds
#   - 13B model: 180-300 seconds
#   - 70B model: Not recommended (too slow)
#
# GPU (8GB VRAM):
#   - 7B model: 10-20 seconds
#   - 13B model: 20-30 seconds
#   - 70B model: Not enough VRAM
#
# GPU (24GB VRAM):
#   - 7B model: 8-15 seconds
#   - 13B model: 15-25 seconds
#   - 70B model: 50-80 seconds
#
# Cloud API (OpenAI/Claude):
#   - Any model: 2-5 seconds
#
# NOTE: Times vary based on:
#   - Form complexity (number of fields)
#   - PDF page count
#   - System load
#   - Model quantization

# ============================================================================
# DOCKER GPU SETUP
# ============================================================================

# NVIDIA GPU (requires nvidia-docker2):
#   docker run --gpus all -v config.ini:/app/config.ini mapper:latest
#
# Specific GPU:
#   docker run --gpus '"device=0"' -v config.ini:/app/config.ini mapper:latest
#
# Multiple GPUs:
#   docker run --gpus '"device=0,1"' -v config.ini:/app/config.ini mapper:latest
#
# Apple Silicon:
#   docker run -v config.ini:/app/config.ini mapper:latest  # MPS auto-detected

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# GPU not detected:
#   1. Check gpu_mode = auto or cuda/mps
#   2. Verify NVIDIA drivers: nvidia-smi
#   3. Check Docker GPU support: docker run --gpus all nvidia/cuda:12.0-base nvidia-smi

# Out of memory:
#   1. Reduce gpu_memory_limit
#   2. Decrease num_gpu_layers (try 20-25)
#   3. Enable low_vram_mode = true
#   4. Use smaller model (mistral instead of llama3.1)

# Slow performance:
#   1. Ensure num_gpu_layers = -1 (all layers on GPU)
#   2. Check gpu_mode is cuda/mps, not cpu
#   3. Verify GPU is actually being used (nvidia-smi or Activity Monitor)
#   4. Try smaller model for faster speed

# Multi-GPU not working:
#   1. Set gpu_device = -1
#   2. Verify all GPUs visible: nvidia-smi
#   3. Check docker --gpus all flag
