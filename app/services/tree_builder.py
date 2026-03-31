import json
import aiosqlite


async def build_tree_for_subject(db: aiosqlite.Connection, subject_id: int) -> dict:
    """Build the reading tree from knowledge_items for a subject.

    Returns {"topicos": [{"titulo": ..., "subtopicos": [{"titulo": ..., "passos": [...]}]}]}
    """
    cursor = await db.execute(
        """
        SELECT ki.library_id, ki.topico, ki.subtopico, ki.acao,
               ki.timestamp, ki.pagina, ki.trecho_referencia, ki.file_path, ki.url
        FROM knowledge_items ki
        JOIN library_items li ON ki.library_id = li.id
        WHERE li.subject_id = ? AND li.deleted_at IS NULL
        ORDER BY ki.topico, ki.subtopico, ki.library_id, ki.timestamp
        """,
        (subject_id,),
    )
    rows = await cursor.fetchall()

    topics_order: list[str] = []
    topics: dict[str, dict[str, list[dict]]] = {}

    for row in rows:
        topico = row["topico"]
        subtopico = row["subtopico"]

        if topico not in topics:
            topics[topico] = {}
            topics_order.append(topico)

        if subtopico not in topics[topico]:
            topics[topico][subtopico] = []

        topics[topico][subtopico].append({
            "library_id": row["library_id"],
            "acao": row["acao"],
            "timestamp": row["timestamp"],
            "pagina": row["pagina"],
            "trecho_referencia": row["trecho_referencia"] or "",
            "file_path": row["file_path"],
            "url": row["url"],
        })

    return {
        "topicos": [
            {
                "titulo": topico,
                "subtopicos": [
                    {"titulo": sub, "passos": passos}
                    for sub, passos in topics[topico].items()
                ],
            }
            for topico in topics_order
        ]
    }


async def rebuild_content_json(db: aiosqlite.Connection, subject_id: int) -> dict:
    """Rebuild and save content_json for a subject. Returns the tree."""
    tree = await build_tree_for_subject(db, subject_id)
    await db.execute(
        "UPDATE subjects SET content_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (json.dumps(tree, ensure_ascii=False), subject_id),
    )
    await db.commit()
    return tree
