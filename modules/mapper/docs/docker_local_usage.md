# Docker Local Usage - Data Flow Guide

## The Problem

When running mapper in Docker locally:
- **Your data** is on local machine (e.g., `/Users/raghava/Documents/data/pdfs/`)
- **Mapper runs** inside Docker container (isolated filesystem)
- **Question**: How does mapper access your local files?

## The Solution: Docker Volume Mounts

Mount your local directories into the Docker container so mapper can access them.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  LOCAL MACHINE (HOST)                                   │
│                                                          │
│  /Users/raghava/Documents/data/                         │
│  ├── input/           ← Your input PDFs & JSON          │
│  ├── output/          ← Mapper writes results here      │
│  └── temp/            ← Temporary files                  │
│                                                          │
│         ▼ VOLUME MOUNT (-v flag)                        │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  DOCKER CONTAINER                                 │  │
│  │                                                    │  │
│  │  /app/data/                                       │  │
│  │  ├── input/     ← Mapped to host input/          │  │
│  │  ├── output/    ← Mapped to host output/         │  │
│  │  └── temp/      ← Mapped to host temp/           │  │
│  │                                                    │  │
│  │  Mapper reads from /app/data/input/               │  │
│  │  Mapper writes to /app/data/output/               │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Method 1: Volume Mounts (RECOMMENDED)

### Basic Usage

```bash
docker run -d \
  -p 8000:8000 \
  -v /Users/raghava/Documents/data:/app/data \
  -e SOURCE_TYPE=local \
  -e OPENAI_API_KEY=your_key \
  --name mapper \
  pdf-autofiller-mapper:latest
```

**What this does:**
- `-v /Users/raghava/Documents/data:/app/data` - Mounts local `/Users/raghava/Documents/data` to container's `/app/data`
- Files in local `data/` folder are now accessible inside container at `/app/data/`
- Changes made by mapper in `/app/data/output/` appear in your local `data/output/` folder

### Multiple Volume Mounts

```bash
docker run -d \
  -p 8000:8000 \
  -v /Users/raghava/Documents/data/input:/app/input \
  -v /Users/raghava/Documents/data/output:/app/output \
  -v /Users/raghava/Documents/data/temp:/app/temp \
  -e SOURCE_TYPE=local \
  -e OPENAI_API_KEY=your_key \
  --name mapper \
  pdf-autofiller-mapper:latest
```

**What this does:**
- Three separate mounts for input, output, and temp directories
- More granular control
- Can have different permissions per directory

### Using Current Directory

```bash
cd /Users/raghava/Documents/data
docker run -d \
  -p 8000:8000 \
  -v $(pwd):/app/data \
  -e SOURCE_TYPE=local \
  -e OPENAI_API_KEY=your_key \
  --name mapper \
  pdf-autofiller-mapper:latest
```

**What this does:**
- `$(pwd)` - Current directory
- Mounts current directory to `/app/data` in container

---

## Method 2: Docker Compose (BEST for Development)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  mapper:
    image: pdf-autofiller-mapper:latest
    container_name: mapper
    ports:
      - "8000:8000"
    volumes:
      # Mount local data directories
      - /Users/raghava/Documents/data/input:/app/data/input
      - /Users/raghava/Documents/data/output:/app/data/output
      - /Users/raghava/Documents/data/temp:/app/data/temp
      
      # Optional: Mount config files
      - ./config.ini:/app/config.ini
    environment:
      - SOURCE_TYPE=local
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

**Usage:**

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f mapper

# Restart
docker-compose restart mapper
```

---

## Method 3: Copy Files (NOT RECOMMENDED)

Only use if you can't use volume mounts (rare).

```bash
# Start container
docker run -d -p 8000:8000 --name mapper pdf-autofiller-mapper:latest

# Copy files INTO container
docker cp /path/to/input.pdf mapper:/app/data/input/

# Run processing via API
curl -X POST http://localhost:8000/mapper/run-all ...

# Copy results OUT of container
docker cp mapper:/app/data/output/filled.pdf /path/to/local/
```

**Why not recommended:**
- Manual copying required
- No real-time sync
- More error-prone
- Loses files when container restarts

---

## Complete Example: Local Development Workflow

### 1. Prepare Local Data Structure

```bash
mkdir -p ~/Documents/pdf-autofiller-data/{input,output,temp}

# Put your files here
cp my-form.pdf ~/Documents/pdf-autofiller-data/input/
cp input-data.json ~/Documents/pdf-autofiller-data/input/
```

### 2. Start Docker with Volume Mounts

```bash
docker run -d \
  --name mapper \
  -p 8000:8000 \
  -v ~/Documents/pdf-autofiller-data:/app/data \
  -e SOURCE_TYPE=local \
  -e OPENAI_API_KEY=sk-xxx \
  pdf-autofiller-mapper:latest

# Check it's running
docker ps
curl http://localhost:8000/health
```

### 3. Use Mapper (Files are Accessible Inside Container)

```bash
# Call API - use paths as they appear INSIDE container
curl -X POST http://localhost:8000/mapper/run-all \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_path": "/app/data/input/my-form.pdf",
    "input_json_path": "/app/data/input/input-data.json",
    "user_id": 1,
    "pdf_doc_id": 100
  }'
```

### 4. Get Results (Automatically on Local Machine)

```bash
# Results are automatically written to local directory
ls -lh ~/Documents/pdf-autofiller-data/output/

# No need to copy - volume mount keeps them in sync!
open ~/Documents/pdf-autofiller-data/output/filled_100.pdf
```

---

## Path Mapping Reference

| Local Machine Path | Container Path | Purpose |
|-------------------|----------------|---------|
| `/Users/raghava/Documents/data` | `/app/data` | Main data directory |
| `/Users/raghava/Documents/data/input` | `/app/data/input` | Input PDFs & JSON |
| `/Users/raghava/Documents/data/output` | `/app/data/output` | Generated files |
| `/Users/raghava/Documents/data/temp` | `/app/data/temp` | Temporary files |

**Important:** When calling API, use **container paths** (not local paths):
- ✅ Correct: `"/app/data/input/form.pdf"`
- ❌ Wrong: `"/Users/raghava/Documents/data/input/form.pdf"`

---

## SDK Integration with Docker

### Option A: SDK on Same Machine as Docker

```python
from pdf_autofiller_sdk import MapperClient

# SDK connects to Docker container's API
client = MapperClient(base_url="http://localhost:8000")

# Prepare local file
local_pdf = "/Users/raghava/Documents/data/input/form.pdf"
local_json = "/Users/raghava/Documents/data/input/data.json"

# Convert to container paths (because of volume mount)
container_pdf = "/app/data/input/form.pdf"
container_json = "/app/data/input/data.json"

# Call mapper (use container paths)
result = client.run_all(
    pdf_path=container_pdf,
    input_json_path=container_json
)

# Result contains container path
filled_pdf_container = result["filled_pdf_path"]  # "/app/data/output/filled_100.pdf"

# Convert to local path
filled_pdf_local = filled_pdf_container.replace("/app/data", "/Users/raghava/Documents/data")
print(f"Filled PDF available at: {filled_pdf_local}")
```

### Option B: SDK on Different Machine

If SDK is on a different machine, use file upload:

```python
# Upload file to Docker container via API
with open("local_form.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post("http://docker-host:8000/upload", files=files)
    uploaded_path = response.json()["path"]

# Process using uploaded path
result = client.run_all(pdf_path=uploaded_path, ...)

# Download result
response = requests.get(f"http://docker-host:8000/download/{result['filled_pdf_path']}")
with open("filled_output.pdf", "wb") as f:
    f.write(response.content)
```

---

## Comparison: Local vs Cloud Storage

### Local Deployment (Docker + Volume Mounts)

```python
# mapper/src/configs/local.py
class LocalStorageConfig:
    def __init__(self):
        self.input_dir = "/app/data/input"    # Inside container
        self.output_dir = "/app/data/output"  # Inside container
        
    def read_file(self, path):
        # Reads from mounted volume
        return open(path, "rb").read()
        
    def write_file(self, path, content):
        # Writes to mounted volume (appears on host immediately)
        with open(path, "wb") as f:
            f.write(content)
```

**Workflow:**
1. User puts files in local `~/data/input/`
2. Volume mount makes them available in container at `/app/data/input/`
3. Mapper processes files
4. Mapper writes to `/app/data/output/` in container
5. Results appear in local `~/data/output/` automatically

### S3 Deployment (Lambda)

```python
# mapper/src/configs/aws.py
class AWSStorageConfig:
    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.bucket = "my-bucket"
        
    def read_file(self, s3_key):
        # Downloads from S3
        response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
        return response["Body"].read()
        
    def write_file(self, s3_key, content):
        # Uploads to S3
        self.s3_client.put_object(Bucket=self.bucket, Key=s3_key, Body=content)
```

**Workflow:**
1. User uploads to S3 bucket
2. Lambda downloads from S3 to `/tmp/` (Lambda's temp storage)
3. Lambda processes files
4. Lambda uploads results back to S3
5. User downloads from S3

---

## Troubleshooting

### "File not found" Error

**Problem:** Mapper can't find `/app/data/input/form.pdf`

**Solutions:**
1. Check volume mount is correct:
   ```bash
   docker inspect mapper | grep -A 5 Mounts
   ```

2. Verify file exists in local directory:
   ```bash
   ls -lh ~/Documents/pdf-autofiller-data/input/
   ```

3. Check file permissions:
   ```bash
   chmod -R 755 ~/Documents/pdf-autofiller-data/
   ```

### "Permission denied" Error

**Problem:** Container can't write to mounted volume

**Solution:** Adjust permissions:
```bash
# Option 1: Give everyone write access (development only)
chmod -R 777 ~/Documents/pdf-autofiller-data/

# Option 2: Match container user (UID 1000 in our Dockerfile)
chown -R 1000:1000 ~/Documents/pdf-autofiller-data/
```

### Volume Mount Not Working on Windows

**Problem:** Windows paths don't work

**Solution:** Use Windows-style paths:
```bash
docker run -v C:\Users\raghava\data:/app/data ...
```

Or use WSL2 paths:
```bash
docker run -v /mnt/c/Users/raghava/data:/app/data ...
```

---

## Best Practices

1. **Always use volume mounts** for local development (not docker cp)
2. **Use absolute paths** for volume mounts (avoid `./relative`)
3. **Use Docker Compose** for easier management
4. **Keep data separate** from code (don't mount entire project)
5. **Set proper permissions** (755 for directories, 644 for files)
6. **Use environment variables** for configuration (not hardcoded paths)
7. **Test volume mounts** before running long operations:
   ```bash
   docker exec mapper ls -lh /app/data/input/
   ```

---

## Summary

**The Answer to Your Question:**

> "When we deploy locally, it should get data from local to docker env to run this things right? SO how do we do this?"

**Answer:** Use Docker **volume mounts** (`-v` flag) to share directories between your local machine and the Docker container. This makes your local files accessible inside the container without copying.

```bash
# This is the key command:
docker run -v /local/path:/container/path image-name

# In your case:
docker run -v ~/Documents/data:/app/data pdf-autofiller-mapper:latest
```

Now mapper inside Docker can read from `/app/data/input/` (which is actually your local `~/Documents/data/input/`) and write to `/app/data/output/` (which appears in your local `~/Documents/data/output/`).

**No S3, no copying, just direct filesystem access via volume mounts!**
