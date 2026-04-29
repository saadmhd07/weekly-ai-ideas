from __future__ import annotations

from abc import ABC, abstractmethod

from genai_newsletter.models import Signal


class Collector(ABC):
    name: str

    @abstractmethod
    def collect(self, limit: int) -> list[Signal]:
        raise NotImplementedError
