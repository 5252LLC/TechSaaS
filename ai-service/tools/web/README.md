# Web Tools for LangChain

## Overview

This package provides tools for web operations that can be used with LangChain agents, including web search, content extraction, and related functionality.

## Components

### Content Extraction Tools

- **WebContentExtractionTool**: Extract and process content from web pages
  - Extracts text, links, images, and metadata
  - Supports filtering for specific HTML elements
  - Handles errors gracefully with detailed feedback

- **StructuredContentExtractionTool**: Extract content based on a specified schema
  - Uses CSS selectors to target specific content
  - Returns structured data ready for agent consumption
  - Perfect for extracting product details, article metadata, etc.

### Search Tools

- **WebSearchTool**: Search the web using Google Custom Search API
  - Requires API key and engine ID for full functionality
  - Returns formatted search results with titles, snippets, and links
  - Configurable number of results

- **NoAPIWebSearchTool**: Fallback web search without requiring API keys
  - Uses web scraping as a fallback mechanism
  - Less reliable but useful when API keys aren't available
  - Automatically used by WebSearchTool when no API credentials are present

### Utility Functions

- **handle_request_error**: Standardized error handling for web requests
- **extract_main_content**: Extract the main content from HTML while removing boilerplate
- **is_valid_url**: Validate URL format
- **create_user_agent**: Generate a realistic user agent string

## Usage Examples

### Web Content Extraction

```python
from tools.web import WebContentExtractionTool

# Initialize the tool
extractor = WebContentExtractionTool()

# Extract content from a web page
result = extractor.run(
    "https://example.com",
    elements=["h1", "p", ".main-content"],  # Optional specific elements to extract
    include_metadata=True  # Include title, links, and images
)

# Access the extracted content
content = result["content"]
metadata = result["metadata"]
```

### Structured Content Extraction

```python
from tools.web import StructuredContentExtractionTool

# Initialize the tool
structured_extractor = StructuredContentExtractionTool()

# Define a schema for extraction
schema = {
    "title": "h1.page-title",
    "price": ".product-price",
    "description": ".product-description",
    "features": ".features li"
}

# Extract structured content
result = structured_extractor.run(
    "https://example.com/product",
    schema=schema
)

# Access the structured data
product_data = result["extracted_data"]
```

### Web Search

```python
from tools.web import WebSearchTool

# Initialize with API credentials
search_tool = WebSearchTool(
    api_key="your_google_api_key",
    engine_id="your_search_engine_id"
)

# Perform a search
results = search_tool.run(
    query="LangChain tutorial",
    num_results=5
)

# Process search results
for result in results:
    print(f"Title: {result['title']}")
    print(f"Link: {result['link']}")
    print(f"Snippet: {result['snippet']}")
    print("---")
```

## Integration with LangChain

These tools can be used directly with LangChain agents:

```python
from langchain_core.agents import AgentExecutor, create_react_agent
from langchain_openai import OpenAI
from tools.web import WebContentExtractionTool, WebSearchTool

# Create tools
tools = [
    WebContentExtractionTool(),
    WebSearchTool(api_key="your_key", engine_id="your_engine")
]

# Create LLM
llm = OpenAI(temperature=0)

# Create agent
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

# Run agent
result = agent_executor.invoke({"input": "Research the latest news about AI and summarize it"})
```

## Error Handling

All tools in this package include robust error handling:

- HTTP errors are handled gracefully with detailed error messages
- Connection errors provide feedback about network issues
- Timeout handling with helpful suggestions
- Invalid URLs are validated before making requests

## Testing

Comprehensive tests are available in `/tests/test_web_tools.py`, covering:

- Content extraction with various scenarios
- Error handling and edge cases
- Structured content extraction
- Web search functionality

## Dependencies

- requests: For HTTP requests
- beautifulsoup4: For HTML parsing
- langchain_core: For tool definitions and callbacks
- pydantic: For input validation

## Security Considerations

- User-Agent management to avoid being blocked by websites
- Rate limiting considerations for search tools
- Proper error handling to avoid exposing sensitive information
- Input validation to prevent security issues
