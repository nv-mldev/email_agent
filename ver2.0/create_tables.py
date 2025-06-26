from core.database import engine, Base

# Import models to register them with Base.metadata
from core.models import EmailProcessingLog  # noqa: F401

print("Creating tables in the database...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully.")
