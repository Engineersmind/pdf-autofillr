# PDF AutoFiller Plugins

**A flexible plugin framework for extending PDF processing capabilities**

## Overview

The `pdf-autofiller-plugins` package provides a comprehensive plugin system that allows you to extend PDF AutoFiller with custom extractors, mappers, validators, fillers, and more.

## Features

- ✅ **7 Plugin Types**: Extractor, Mapper, Chunker, Embedder, Validator, Filler, Transformer
- ✅ **Auto-Discovery**: Automatically find and load plugins
- ✅ **Zero Dependencies**: Pure Python, no external dependencies
- ✅ **Type-Safe**: Full type hints and ABC interfaces
- ✅ **Priority System**: Control plugin loading order
- ✅ **Lazy Loading**: Load plugins on-demand for better performance
- ✅ **Configuration**: Plugin-specific configuration support
- ✅ **Lifecycle Management**: Initialize, execute, shutdown hooks

## Installation

```bash
cd packages/plugins
pip install -e .
```

## Quick Start

### Creating a Custom Plugin

```python
from pdf_autofiller_plugins import plugin
from pdf_autofiller_plugins.interfaces import ExtractorPlugin

@plugin(
    category="extractor",
    name="my-extractor",
    version="1.0.0",
    description="My custom PDF extractor"
)
class MyExtractorPlugin(ExtractorPlugin):
    
    def supports(self, pdf_path: str, **kwargs) -> bool:
        # Check if we can handle this PDF
        return "special" in pdf_path.lower()
    
    def extract(self, pdf_path: str, **kwargs):
        # Your extraction logic
        return {
            "fields": [...],
            "metadata": {...},
            "extractor": "my-extractor"
        }
```

### Using Plugins

```python
from pdf_autofiller_plugins import PluginManager

# Initialize manager
manager = PluginManager(
    plugin_paths=["my_plugins", "user_plugins"],
    lazy_load=True
)

# Discover plugins
discovered = manager.discover_plugins(["my_plugins"])

# Find suitable extractor
extractor = manager.find_extractor("special_form.pdf")
if extractor:
    result = extractor.extract("special_form.pdf")
```

## Plugin Types

### 1. ExtractorPlugin
Extract structured data from PDFs.

```python
from pdf_autofiller_plugins.interfaces import ExtractorPlugin

class MyExtractor(ExtractorPlugin):
    def extract(self, pdf_path: str, **kwargs):
        # Return extracted fields
        pass
    
    def supports(self, pdf_path: str, **kwargs) -> bool:
        # Check if this PDF is supported
        pass
```

### 2. MapperPlugin
Map extracted fields to target schemas.

```python
from pdf_autofiller_plugins.interfaces import MapperPlugin

class MyMapper(MapperPlugin):
    def map_fields(self, extracted_fields, target_schema, **kwargs):
        # Return mapped fields
        pass
    
    def supports_schema(self, schema) -> bool:
        # Check if schema is supported
        pass
```

### 3. ValidatorPlugin
Validate field values.

```python
from pdf_autofiller_plugins.interfaces import ValidatorPlugin

class EmailValidator(ValidatorPlugin):
    def validate(self, field_name, field_value, rules, **kwargs):
        # Return validation results
        pass
    
    def supports_field_type(self, field_type: str) -> bool:
        return field_type == "email"
```

### 4. FillerPlugin
Fill PDFs with data.

```python
from pdf_autofiller_plugins.interfaces import FillerPlugin

class MyFiller(FillerPlugin):
    def fill(self, pdf_path, data, output_path, **kwargs):
        # Fill PDF and return results
        pass
    
    def supports_pdf_type(self, pdf_path: str) -> bool:
        # Check if PDF type is supported
        pass
```

### 5. ChunkerPlugin
Split PDFs into chunks.

### 6. EmbedderPlugin
Embed metadata into PDFs.

### 7. TransformerPlugin
Transform field values.

## Decorators

### @plugin
Register a class as a plugin.

```python
@plugin(
    category="extractor",
    name="my-extractor",
    version="1.0.0",
    author="Your Name",
    description="My custom extractor",
    tags=["invoice", "financial"],
    priority=200,  # Higher = loaded first
    enabled=True
)
class MyPlugin(ExtractorPlugin):
    pass
```

### @requires
Specify plugin dependencies.

```python
from pdf_autofiller_plugins.decorators import requires

@requires("numpy", "pandas")
class MLPlugin(MapperPlugin):
    pass
```

### @cache_result
Cache plugin results.

```python
from pdf_autofiller_plugins.decorators import cache_result

class MyPlugin(ExtractorPlugin):
    @cache_result(ttl=3600)
    def extract(self, pdf_path, **kwargs):
        # Expensive operation
        pass
```

## Plugin Manager

### Initialization

```python
manager = PluginManager(
    plugin_paths=["my_plugins", "user_plugins"],
    enabled_plugins=["plugin1", "plugin2"],  # None = all enabled
    lazy_load=True  # Load on-demand vs at startup
)
```

### Discovery

```python
# Discover from paths
discovered = manager.discover_plugins(
    search_paths=["my_plugins"],
    categories=["extractor", "mapper"]  # None = all categories
)

# Result: {'extractor': ['plugin1', 'plugin2'], ...}
```

### Loading Plugins

```python
# Load specific plugin
plugin = manager.load_plugin("my-extractor", "extractor")

# Get already loaded plugin
plugin = manager.get_plugin("my-extractor", "extractor")

# Unload plugin
manager.unload_plugin("my-extractor", "extractor")
```

### Finding Plugins

```python
# Find best extractor for PDF
extractor = manager.find_extractor("invoice.pdf")

# Find best mapper for schema
mapper = manager.find_mapper(target_schema)
```

### Plugin Info

```python
# List all plugins
all_plugins = manager.list_plugins()
# {'extractor': ['plugin1', 'plugin2'], ...}

# Get plugin metadata
info = manager.get_plugin_info("my-extractor", "extractor")
# {'name': '...', 'version': '...', 'author': '...', ...}
```

### Lifecycle

```python
# Shutdown all plugins
manager.shutdown()
```

## Configuration

Plugins can accept configuration:

```python
# Load with config
plugin = manager.load_plugin(
    "my-extractor",
    "extractor",
    config={
        "api_key": "...",
        "endpoint": "...",
        "timeout": 30
    }
)

# Access in plugin
class MyPlugin(ExtractorPlugin):
    def extract(self, pdf_path, **kwargs):
        api_key = self.get_config_value("api_key")
        # Use api_key...
```

## Examples

See the `examples/` directory for complete examples:

- `invoice_extractor_plugin.py` - Custom invoice extractor
- `ml_mapper_plugin.py` - ML-based field mapper  
- `email_validator_plugin.py` - Email validator
- `using_plugins.py` - Complete usage example

## Integration with Mapper Module

```python
# In modules/mapper/src/operations.py

from pdf_autofiller_plugins import PluginManager

class ExtractHandler:
    def __init__(self):
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins(["user_plugins"])
    
    def execute(self, request):
        # Try to find custom extractor
        extractor = self.plugin_manager.find_extractor(request.pdf_path)
        
        if extractor:
            # Use plugin
            result = extractor.extract(request.pdf_path)
        else:
            # Fall back to default
            result = self.default_extract(request.pdf_path)
        
        return result
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
black pdf_autofiller_plugins/

# Sort imports
isort pdf_autofiller_plugins/

# Type checking
mypy pdf_autofiller_plugins/
```

## Architecture

```
packages/plugins/
├── pdf_autofiller_plugins/
│   ├── __init__.py              # Package exports
│   ├── manager.py               # PluginManager
│   ├── registry.py              # PluginRegistry
│   ├── decorators.py            # @plugin, @requires, etc.
│   └── interfaces/
│       ├── base_plugin.py       # BasePlugin ABC
│       ├── extractor_plugin.py  # ExtractorPlugin ABC
│       ├── mapper_plugin.py     # MapperPlugin ABC
│       ├── chunker_plugin.py    # ChunkerPlugin ABC
│       ├── embedder_plugin.py   # EmbedderPlugin ABC
│       ├── validator_plugin.py  # ValidatorPlugin ABC
│       ├── filler_plugin.py     # FillerPlugin ABC
│       └── transformer_plugin.py # TransformerPlugin ABC
├── examples/                    # Example plugins
├── setup.py                     # Package setup
└── README.md                    # This file
```

## Best Practices

1. **Use @plugin decorator** - Provides metadata and registration
2. **Implement supports()** - Let system find best plugin
3. **Return consistent format** - Follow interface contract
4. **Handle errors gracefully** - Don't crash host application
5. **Document config schema** - Help users configure plugin
6. **Test thoroughly** - Ensure plugin works in isolation
7. **Set appropriate priority** - Control loading order

## FAQ

**Q: Can plugins have dependencies?**  
A: Yes, use `@requires("package1", "package2")` decorator.

**Q: How are plugins discovered?**  
A: Plugins are found by scanning module paths for classes with `@plugin` decorator.

**Q: Can I have multiple plugins for the same task?**  
A: Yes! The system will use priority and `supports()` to choose the best one.

**Q: Are plugins sandboxed?**  
A: No, plugins run in same process. Be careful with untrusted plugins.

**Q: Can plugins call other plugins?**  
A: Yes, access `PluginManager` to load and use other plugins.

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! See CONTRIBUTING.md for guidelines.

---

**Built for PDF AutoFiller** 🚀
