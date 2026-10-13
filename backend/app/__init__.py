import os

from dotenv import load_dotenv

load_dotenv()


def env(name: str) -> str:
    """Required setting; a clear message beats a bare KeyError when a deploy is missing one."""
    if not os.environ.get(name):
        raise RuntimeError(f"{name} is not set on the server")
    return os.environ[name]
