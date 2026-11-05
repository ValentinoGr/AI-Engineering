from rag_system import rag_system

resultados = rag_system.obtener_top_k("¿Cuántos días de vacaciones tengo con 6 años de antigüedad?")

for i, r in enumerate(resultados, 1):
    print(f"{i}. [{r['fuente']}] {r['contenido'][:120]}...")

print("💬 Modo interactivo — consultá el sistema RAG híbrido (BM25 + Pinecone)")
print("   (escribí 'salir' para terminar)\n")

while True:
    pregunta_usuario = input("🧑 Vos: ").strip()

    if pregunta_usuario.lower() in ("salir", "exit", "quit", ""):
        print("\n👋 Listo, terminamos la sesión.")
        break

    resultados = rag_system.obtener_top_k(pregunta_usuario)

    if not resultados:
        print("⚠️ No se recuperó ningún fragmento.\n")
        continue

    print(f"\n📎 Top {len(resultados)} fragmentos recuperados:")
    for i, r in enumerate(resultados, 1):
        print(f"\n  {i}. [{r['fuente']} | {r['categoria']}]")
        print(f"     {r['contenido'][:200]}{'...' if len(r['contenido']) > 200 else ''}")
    print("-" * 80)
