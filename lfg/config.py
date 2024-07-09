import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

from lfg.codediff.git_wrappers import is_git_installed


@dataclass
class Config:
    model_temperature: float = 0.0
    model_name: str = "gpt-3.5-turbo"
    git_installed: bool = False
    client: OpenAI = None
    model_enabled: bool = False

    @classmethod
    def create(cls):
        return cls(
            git_installed=is_git_installed(),
            client=OpenAI(api_key=os.getenv("OPENAI_API_KEY")),
            model_enabled=os.getenv("OPENAI_API_KEY") is not None,
        )


def load_config() -> Config:
    load_dotenv()
    return Config.create()
