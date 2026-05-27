from abc import ABC, abstractmethod

class CharacterPlugin(ABC):
    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def get_response_style(self):
        pass

    @abstractmethod
    def get_animations(self, mood):
        pass
