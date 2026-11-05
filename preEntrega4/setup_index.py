import os

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  # dimensión de este modelo — el índice de Pinecone debe coincidir exacto

embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

INDEX_NAME = os.getenv("INDEX_NAME", "techcorp-rag-hibrido")
NAMESPACE = "politicas-internas"

indices_existentes = [i["name"] for i in pc.list_indexes()]

if INDEX_NAME not in indices_existentes:
    print(f"🆕 Creando índice '{INDEX_NAME}' (dimensión {EMBEDDING_DIM})...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBEDDING_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
else:
    print(f"♻️ El índice '{INDEX_NAME}' ya existe — no se vuelve a crear")

indice = pc.Index(INDEX_NAME)
print(indice.describe_index_stats())
