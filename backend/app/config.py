"""
Central configuration for Trinetra backend.
Reads from environment variables (see .env.example at repo root).
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Postgres
    postgres_user: str = "trinetra"
    postgres_password: str = "changeme"
    postgres_db: str = "trinetra"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Neo4j
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"
    use_neo4j: bool = True  # False forces NetworkX fallback everywhere

    # ML safety valve (see docs: Day 11 checkpoint)
    use_graphsage: bool = True  # False forces Node2Vec fallback

    # CORS
    cors_origins: str = "http://localhost:5173"

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
