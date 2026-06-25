"""Interface neutra de LLM e o stub do pipeline interno do banco."""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Troque o provider sem tocar no pipeline."""
    @abstractmethod
    def resumir(self, system_prompt: str, user_content: str) -> str:
        """Retorna uma STRING contendo APENAS o JSON pedido pelo system prompt."""
        ...


class PipelineIANaoAcoplado(LLMClient):
    """
    Placeholder. O modelo real é INTERNO do banco e será acoplado depois.
    Para acoplar, crie uma classe que herde de LLMClient:

        class ModeloInternoBanco(LLMClient):
            def __init__(self, endpoint, token):
                self.endpoint, self.token = endpoint, token
            def resumir(self, system_prompt, user_content) -> str:
                # POST no endpoint interno; devolver a string JSON do modelo
                ...

    Contrato do retorno: string com APENAS o JSON do schema; sem markdown;
    idealmente temperatura 0 (extração factual determinística).
    """
    def resumir(self, system_prompt: str, user_content: str) -> str:
        raise NotImplementedError(
            "Pipeline de IA ainda não acoplado. Implemente um LLMClient com o "
            "modelo interno do banco."
        )
