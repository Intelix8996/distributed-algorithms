from typing import Protocol


class KeyValueStorage[K, V](Protocol):
    def set(self, key: K, value: V): ...
    def delete(self, key: K): ...
    def query(self, key: K) -> V | None: ...


class DictStorage[K, V]:
    _storage: dict[K, V]

    def __init__(self) -> None:
        self._storage = {}

    def set(self, key: K, value: V):
        self._storage[key] = value

    def delete(self, key: K):
        del self._storage[key]

    def query(self, key: K) -> V | None:
        return self._storage.get(key)
    
    def __repr__(self) -> str:
        return str(self._storage)
