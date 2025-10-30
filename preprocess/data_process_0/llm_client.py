"""LLM client for connecting to local Qwen model."""
from langchain_openai import ChatOpenAI
from typing import Optional
from config import (
    LOCAL_QWEN_ENDPOINT,
    LOCAL_QWEN_MODEL_NAME,
    LOCAL_QWEN_API_KEY,
    NODE_MODELS
)


def get_llm(
    node_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    endpoint: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None
):
    """
    Get LLM client configured for local Qwen model.
    
    Args:
        node_name: Name of the node to get model configuration for
        temperature: Temperature for model sampling (overrides node config)
        max_tokens: Maximum tokens to generate (overrides node config)
        endpoint: API endpoint (overrides node config)
        model_name: Model name (overrides node config)
        api_key: API key (overrides node config)
        
    Returns:
        ChatOpenAI instance configured for local Qwen endpoint
    """
    # Get node-specific configuration if provided
    if node_name and node_name in NODE_MODELS:
        node_config = NODE_MODELS[node_name]
        endpoint = endpoint or node_config.get("endpoint")
        model_name = model_name or node_config.get("model_name")
        api_key = api_key or node_config.get("api_key")
        # Only use node config if not explicitly provided
        if temperature is None:
            temperature = node_config.get("temperature")
        if max_tokens is None:
            max_tokens = node_config.get("max_tokens")
    else:
        # Use defaults
        endpoint = endpoint or LOCAL_QWEN_ENDPOINT
        model_name = model_name or LOCAL_QWEN_MODEL_NAME
        api_key = api_key or LOCAL_QWEN_API_KEY
    
    # Build kwargs for ChatOpenAI
    llm_kwargs = {
        "base_url": endpoint,
        "model": model_name,
        "api_key": api_key,
    }
    
    # Only add temperature and max_tokens if they are provided
    if temperature is not None:
        llm_kwargs["temperature"] = temperature
    if max_tokens is not None:
        llm_kwargs["max_tokens"] = max_tokens
    
    llm = ChatOpenAI(**llm_kwargs)
    return llm


if __name__ == "__main__":
    # Test the LLM connection
    llm = get_llm()
    response = llm.invoke("Hello! Please introduce yourself.")
    print(f"Response: {response.content}")