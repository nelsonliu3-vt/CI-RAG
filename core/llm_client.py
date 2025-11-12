"""
OpenAI LLM Client with o1-mini (gpt-5-mini) Support
Handles API calls with proper configuration for reasoning models
"""

from openai import OpenAI, APIError, RateLimitError, APIConnectionError, APITimeoutError
from typing import Dict, Any, Optional
import logging

from core.config import OPENAI_API_KEY, MODEL_CONFIG, DEFAULT_MODEL

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMClient:
    """OpenAI client wrapper with o1-mini support"""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        """
        Initialize LLM client

        Args:
            model_name: Model to use (default: gpt-5-mini)
        """
        self.client = OpenAI(api_key=OPENAI_API_KEY, timeout=60, max_retries=2)
        self.model_name = model_name
        self.model_config = MODEL_CONFIG.get(model_name)

        if not self.model_config:
            raise ValueError(f"Model {model_name} not found in MODEL_CONFIG")

        logger.info(f"Initialized LLM client with model: {model_name}")

    def chat_completion(
        self,
        messages: list[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Generate chat completion

        Args:
            messages: List of message dicts with "role" and "content"
            **kwargs: Additional parameters (overrides config)

        Returns:
            str: Generated response
        """
        # Build request parameters based on model type
        request_params = {
            "model": self.model_config["model"],
            "messages": messages
        }

        # Check if this is gpt-5-mini (uses max_completion_tokens + reasoning_effort like o1-mini)
        if self.model_name == "gpt-5-mini":
            request_params["max_completion_tokens"] = kwargs.get(
                "max_completion_tokens",
                self.model_config["max_completion_tokens"]
            )
            request_params["reasoning_effort"] = kwargs.get(
                "reasoning_effort",
                self.model_config["reasoning_effort"]
            )
        else:
            # Standard GPT models use max_tokens + temperature
            request_params["max_tokens"] = kwargs.get(
                "max_tokens",
                self.model_config.get("max_tokens", 3000)
            )
            request_params["temperature"] = kwargs.get(
                "temperature",
                self.model_config.get("temperature", 0.7)
            )

        try:
            response = self.client.chat.completions.create(**request_params)
            return response.choices[0].message.content

        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise RuntimeError("API rate limit exceeded. Please try again in a moment.") from e
        except APITimeoutError as e:
            logger.error(f"OpenAI API timeout: {e}")
            raise TimeoutError("LLM request timed out. Please try again.") from e
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            raise ConnectionError("Cannot connect to OpenAI API. Check your network.") from e
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error in chat completion: {str(e)}")
            raise

    def generate(
        self,
        system: str,
        user: str,
        **kwargs
    ) -> str:
        """
        Generate response with system and user prompts

        Args:
            system: System prompt
            user: User prompt
            **kwargs: Additional parameters

        Returns:
            str: Generated response
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]

        return self.chat_completion(messages, **kwargs)

    def generate_with_context(
        self,
        prompt_template: str,
        context: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        Generate response with template and context

        Args:
            prompt_template: Template string with {placeholders}
            context: Dictionary of values to fill in template
            **kwargs: Additional parameters

        Returns:
            str: Generated response
        """
        # Fill in template
        prompt = prompt_template.format(**context)

        # Generate with simple user message (no system)
        messages = [{"role": "user", "content": prompt}]

        return self.chat_completion(messages, **kwargs)


# Singleton instance
_client_instance: Optional[LLMClient] = None


def get_llm_client(model_name: str = DEFAULT_MODEL) -> LLMClient:
    """
    Get or create LLM client singleton

    Args:
        model_name: Model to use

    Returns:
        LLMClient instance
    """
    global _client_instance

    if _client_instance is None or _client_instance.model_name != model_name:
        _client_instance = LLMClient(model_name)

    return _client_instance


if __name__ == "__main__":
    # Test the client
    print("Testing LLM client with gpt-5-mini (o1-mini)...")

    client = get_llm_client("gpt-5-mini")

    response = client.generate(
        system="You are a helpful assistant.",
        user="What is 2+2? Answer in one word."
    )

    print(f"Response: {response}")
    print("✓ LLM client test successful!")
