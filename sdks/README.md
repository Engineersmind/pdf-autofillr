# SDKs

OpenAPI specifications and non-Python client SDKs.

---

## OpenAPI specs

Machine-readable API contracts for each module. Used to generate clients in any language.

| File | Module | Status |
|------|--------|--------|
| `openapi-mapper.yaml` | Mapper | Complete |
| `openapi-chatbot.yaml` | Chatbot | Skeleton |
| `openapi-rag.yaml` | RAG | Skeleton |
| `openapi-upload.yaml` | PDF Upload | Skeleton |

---

## Python SDK

The Python SDK lives **inside the mapper module**, not here.

```bash
pip install pdf-autofiller-mapper           # HTTP client
pip install pdf-autofiller-mapper[embedded] # + in-process pipeline
```

Source: [`modules/mapper/sdk/`](../modules/mapper/sdk/)

---

## TypeScript SDK

Skeleton in `typescript/`. Generate from the OpenAPI spec when ready:

```bash
npm install @openapitools/openapi-generator-cli -g
openapi-generator generate \
  -i openapi-mapper.yaml \
  -g typescript-axios \
  -o typescript/generated \
  --additional-properties=npmName=@engineersmind/pdf-autofiller-sdk,npmVersion=1.0.0
```

---

## Generating other language clients

Use `generate.sh` or run `openapi-generator` directly against any spec:

```bash
# Go
openapi-generator generate -i openapi-mapper.yaml -g go -o go/

# Java
openapi-generator generate -i openapi-mapper.yaml -g java -o java/
```

Install OpenAPI Generator: `brew install openapi-generator` or `npm install @openapitools/openapi-generator-cli -g`
