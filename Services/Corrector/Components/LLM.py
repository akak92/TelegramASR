"""
LLM.py

Encapsula el acceso a Azure OpenAI para corregir y formatear transcripciones
médicas provenientes de Azure Speech AI.
"""

import os
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion
from dotenv import load_dotenv


class LLM:
    def __init__(self):
        load_dotenv()

        self.client: AzureOpenAI = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_KEY", ""),
            api_version=os.getenv("AZURE_OPENAI_VERSION", "2024-12-01-preview"),
        )
        self.deployment: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.3-chat")

        prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/prompt.txt")
        with open(prompt_path, encoding="utf-8") as f:
            self.system_prompt: str = f.read().strip()

    def correct(self, transcription: str) -> str:
        """
        Corrige y formatea una transcripción médica cruda.

        Args:
            transcription: Texto crudo producido por Azure Speech AI.

        Returns:
            Informe médico corregido y formateado listo para Telegram.
        """
        messages: list = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": transcription},
        ]
        completion: ChatCompletion = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            stream=False,
        )
        return completion.choices[0].message.content.strip()
