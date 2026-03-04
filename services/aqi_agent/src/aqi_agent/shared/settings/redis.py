from __future__ import annotations

from pydantic import BaseModel


class RedisSettings(BaseModel):
    host: str = 'localhost'
    port: int = 6379
    db: int = 0
    password: str | None = None
    ssl: bool = False

    @property
    def url(self) -> str:
        scheme = 'rediss' if self.ssl else 'redis'
        if self.password:
            return f'{scheme}://:{self.password}@{self.host}:{self.port}/{self.db}'
        return f'{scheme}://{self.host}:{self.port}/{self.db}'
