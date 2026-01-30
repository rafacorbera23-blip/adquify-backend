
from qdrant_client import QdrantClient
import logging

logging.basicConfig(level=logging.INFO)

def main():
    client = QdrantClient(location=":memory:")
    print("--- QdrantClient methods ---")
    methods = [m for m in dir(client) if not m.startswith("_")]
    print(methods)
    
    # Check version if possible
    import qdrant_client
    print(f"Version: {getattr(qdrant_client, '__version__', 'Unknown')}")

if __name__ == "__main__":
    main()
