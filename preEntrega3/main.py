import asyncio

from rag_chain import get_rag_response, retriever


async def main():
    # Prueba rápida del retriever solo
    resultados_prueba = retriever.invoke("¿Cuántos días de vacaciones tengo?")
    for i, doc in enumerate(resultados_prueba, 1):
        print(f"--- Fragmento {i} (fuente: {doc.metadata['source']}) ---")
        print(doc.page_content[:150], "...\n")

    respuesta_ok = await get_rag_response("¿Cuántos días de vacaciones corresponden a un empleado con 5 años de antigüedad?")

    print("RESPUESTA:", respuesta_ok.respuesta)
    print("FUENTES:", respuesta_ok.fuentes)
    print("Fragmentos usados:", respuesta_ok.fragmentos_recuperados)

    respuesta_trampa = await get_rag_response("¿Cuál es la política de bonos por rendimiento anual en TechCorp?")

    print("RESPUESTA:", respuesta_trampa.respuesta)
    print("FUENTES:", respuesta_trampa.fuentes)
    print("Fragmentos usados:", respuesta_trampa.fragmentos_recuperados)

    print("💬 Modo interactivo — escribí tu pregunta sobre las políticas de TechCorp")
    print("   (escribí 'salir' para terminar)\n")

    while True:
        pregunta_usuario = input("🧑 Vos: ").strip()

        if pregunta_usuario.lower() in ("salir", "exit", "quit", ""):
            print("\n👋 Listo, terminamos la sesión.")
            break

        resultado = await get_rag_response(pregunta_usuario)

        print("\n🤖 Respuesta:")
        print(resultado.respuesta)

        if resultado.fuentes:
            print(f"\n📎 Fuentes: {', '.join(resultado.fuentes)}")

        print(f"🔢 Fragmentos usados: {resultado.fragmentos_recuperados}")
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(main())
