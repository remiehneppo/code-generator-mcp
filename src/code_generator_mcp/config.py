import os
import sys
import argparse

class Config:
    def __init__(self):
        self.api_url = "https://api.openai.com/v1"
        self.model = "gpt-4o"
        self.api_key = ""

    def load(self):
        # 1. Parse command line arguments using parse_known_args
        # to prevent conflicts with FastMCP or pytest arguments.
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--api-url", default=None, help="OpenAI-compatible API URL")
        parser.add_argument("--model", default=None, help="Model name")
        parser.add_argument("--api-key", default=None, help="API Key (optional)")
        
        args, remaining_args = parser.parse_known_args()

        # 2. Extract configuration with fallback to environment variables
        self.api_url = (
            args.api_url
            or os.environ.get("CODE_GEN_API_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        )
        self.model = (
            args.model
            or os.environ.get("CODE_GEN_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or "gpt-4o"
        )
        self.api_key = (
            args.api_key
            or os.environ.get("CODE_GEN_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or ""
        )

        if args.api_key:
            sys.stderr.write(
                "WARNING: Passing secrets via command-line arguments is insecure. "
                "Please use the environment variable CODE_GEN_API_KEY instead.\n"
            )

        # 3. Clean sys.argv if NOT running in pytest, so FastMCP CLI parser is not confused
        is_testing = "pytest" in sys.modules or any("pytest" in arg or "py.test" in arg for arg in sys.argv)
        if not is_testing:
            sys.argv = [sys.argv[0]] + remaining_args

config = Config()
