# Examples

## mapper_direct_usage.py — Embedded SDK (in-process)

Uses `PDFMapper` from the `pdf-autofiller-mapper` SDK to run the full pipeline inside your Python process. No server needed.

```bash
pip install pdf-autofiller-mapper[embedded]
# Java 17+ must be on PATH

cp modules/mapper/config.ini.example modules/mapper/config.ini
# set llm_model and your API key

python examples/mapper_direct_usage.py
```

## mapper_api_usage.py — HTTP client SDK

Uses `PDFMapperClient` to talk to a running server (local or Docker).

```bash
pip install pdf-autofiller-mapper

# Start server
cd modules/mapper && python api_server.py

# Run example
python examples/mapper_api_usage.py
```

## More examples

See `modules/mapper/sdk/examples/` for additional SDK patterns.
