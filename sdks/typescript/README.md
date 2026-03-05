# PDF Autofiller TypeScript SDK

TypeScript/JavaScript client for PDF Autofiller API (Mapper Module).

## Installation

```bash
npm install @engineersmind/pdf-autofiller-sdk
# or
yarn add @engineersmind/pdf-autofiller-sdk
```

## Usage

```typescript
import { PDFMapperClient } from '@engineersmind/pdf-autofiller-sdk';

const client = new PDFMapperClient({
  apiKey: 'your-api-key',
  baseURL: 'https://api.example.com/v1'
});

// Extract fields
const result = await client.mapper.extract({
  pdfPath: 's3://bucket/form.pdf'
});

// Map fields
const mapResult = await client.mapper.map({
  pdfPath: 's3://bucket/form.pdf',
  mapperType: 'ensemble'
});

// Fill PDF
const fillResult = await client.mapper.fill({
  pdfPath: 's3://bucket/form.pdf',
  data: {
    firstName: 'John',
    lastName: 'Doe'
  }
});
```

## TODO

Complete implementation after generating from OpenAPI spec with:
- [Stainless](https://www.stainlessapi.com/)
- [OpenAPI Generator](https://openapi-generator.tech/)

See `../openapi-mapper.yaml` for API specification.

## License

MIT
