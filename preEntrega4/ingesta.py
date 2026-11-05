import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from setup_index import INDEX_NAME, NAMESPACE, embeddings, indice

loader = DirectoryLoader("data", glob="*.txt", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
documentos_crudos = loader.load()

splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=600,      # dentro del rango 500-800 tokens sugerido
    chunk_overlap=100,
)

chunks = splitter.split_documents(documentos_crudos)

# Metadata avanzada: fuente, categoría (derivada del nombre de archivo) e índice de chunk
for i, chunk in enumerate(chunks):
    nombre_archivo = os.path.basename(chunk.metadata["source"])
    chunk.metadata["source"] = nombre_archivo
    chunk.metadata["categoria"] = nombre_archivo.replace(".txt", "").replace("_", " ")
    chunk.metadata["chunk_id"] = i

print(f"✂️ Fragmentos generados: {len(chunks)}")
print("Metadata de ejemplo:", chunks[0].metadata)

if __name__ == "__main__":
    vectorstore = PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=INDEX_NAME,
        namespace=NAMESPACE,
    )

    print("📦 Vectores en el namespace:", indice.describe_index_stats()["namespaces"].get(NAMESPACE, {}))
