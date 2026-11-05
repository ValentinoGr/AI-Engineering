import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Cargar todos los .txt de /data
loader = DirectoryLoader("data", glob="*.txt", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
documentos_crudos = loader.load()

print(f"📄 Documentos cargados: {len(documentos_crudos)}")

# 2. Fragmentar respetando el mínimo pedido: 500 tokens, 50 de overlap
splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=500,
    chunk_overlap=70,
)

chunks = splitter.split_documents(documentos_crudos)

print(f"✂️ Fragmentos generados: {len(chunks)}")
print("\n--- Ejemplo de fragmento ---")
print(chunks[0].page_content[:300])
print("Metadata:", chunks[0].metadata)

PERSIST_DIR = "./vectorstore"
COLLECTION_NAME = "techcorp_policies"

# ⚠️ Mismo modelo de embeddings para indexar Y para consultar (evita el error #1 de la consigna)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

ya_existe_indice = os.path.exists(PERSIST_DIR) and len(os.listdir(PERSIST_DIR)) > 0

if ya_existe_indice:
    print("♻️ Índice existente detectado — cargando sin reindexar")
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )
else:
    print("🆕 No hay índice previo — indexando documentos por primera vez")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIR,
    )

print(f"📦 Documentos en la colección: {vectorstore._collection.count()}")
