class Versioning:
    def __init__(self, name: str) -> None:
        self._name = name

    def __repr__(self) -> str:
        return f"<Versioning {self._name}>"


AUTO_VERSION = Versioning("AUTO_VERSION")
ANY_VERSION = Versioning("ANY_VERSION")
