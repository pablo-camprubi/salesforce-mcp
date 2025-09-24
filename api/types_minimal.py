"""
Minimal types for MCP compatibility without full MCP library dependency
"""

class TextContent:
    def __init__(self, type: str, text: str):
        self.type = type
        self.text = text

class Tool:
    def __init__(self, name: str, description: str, inputSchema: dict):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema
