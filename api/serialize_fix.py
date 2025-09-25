def serialize_response(obj):
    """Convert TextContent objects and other non-serializable objects to JSON-serializable format"""
    if hasattr(obj, 'type') and hasattr(obj, 'text'):
        # Handle TextContent objects
        return {"type": obj.type, "text": obj.text}
    elif isinstance(obj, dict):
        if "content" in obj and isinstance(obj["content"], list):
            # Handle tool call response with content array
            return {
                **obj,
                "content": [serialize_response(item) for item in obj["content"]]
            }
        else:
            return {key: serialize_response(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_response(item) for item in obj]
    else:
        return obj
