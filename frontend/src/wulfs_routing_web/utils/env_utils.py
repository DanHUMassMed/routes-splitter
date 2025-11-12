import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_env(var_name: str, default: str = None) -> str:
    """
    Retrieves the value of an environment variable after ensuring .env files are loaded.

    Args:
        var_name: The name of the environment variable.
        default: The default value to return if the environment variable is not set.

    Returns:
        The value of the environment variable, or the default value if not set.
    """
    return os.getenv(var_name, default)
