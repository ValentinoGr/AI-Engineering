import json
import os
from typing import Dict, List

from rag_system import RAGSystem, rag_system

RUTA_GOLDEN_SET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_set.json")

with open(RUTA_GOLDEN_SET, encoding="utf-8") as f:
    golden_set = json.load(f)


def evaluar(rag_system: RAGSystem, golden_set: List[Dict]) -> Dict:
    resultados_por_pregunta = []

    for caso in golden_set:
        top_k = rag_system.obtener_top_k(caso["pregunta"])
        fuentes_recuperadas = [r["fuente"] for r in top_k]

        # Recall@5: ¿el documento esperado aparece entre los recuperados? (0 o 1)
        recall = 1.0 if caso["documento_id_esperado"] in fuentes_recuperadas else 0.0

        # Precision@5: qué % de los 5 recuperados son "útiles" (coinciden con la fuente esperada)
        coincidencias = sum(1 for f in fuentes_recuperadas if f == caso["documento_id_esperado"])
        precision = coincidencias / len(top_k) if top_k else 0.0

        resultados_por_pregunta.append({
            "pregunta": caso["pregunta"],
            "esperado": caso["documento_id_esperado"],
            "recuperados": fuentes_recuperadas,
            "recall@5": recall,
            "precision@5": precision,
        })

    recall_promedio = sum(r["recall@5"] for r in resultados_por_pregunta) / len(resultados_por_pregunta)
    precision_promedio = sum(r["precision@5"] for r in resultados_por_pregunta) / len(resultados_por_pregunta)

    return {
        "detalle": resultados_por_pregunta,
        "recall@5_promedio": recall_promedio,
        "precision@5_promedio": precision_promedio,
    }


if __name__ == "__main__":
    reporte = evaluar(rag_system, golden_set)

    print("=" * 80)
    for r in reporte["detalle"]:
        estado = "✅" if r["recall@5"] == 1.0 else "❌"
        print(f"{estado} {r['pregunta']}")
        print(f"   Esperado: {r['esperado']} | Recuperados: {r['recuperados']}")
        print(f"   Recall@5: {r['recall@5']:.0%} | Precision@5: {r['precision@5']:.0%}\n")

    print("=" * 80)
    print(f"📊 RECALL@5 PROMEDIO:    {reporte['recall@5_promedio']:.1%}")
    print(f"📊 PRECISION@5 PROMEDIO: {reporte['precision@5_promedio']:.1%}")
