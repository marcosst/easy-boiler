import aiosqlite


async def get_taxonomy_for_subject(db: aiosqlite.Connection, subject_id: int) -> dict:
    """Extract minimal taxonomy (topics + subtopic names) for a subject.

    Returns {"topicos": [{"titulo": "...", "subtopicos": ["...", ...]}]}
    """
    cursor = await db.execute(
        """
        SELECT DISTINCT ki.topico, ki.subtopico
        FROM knowledge_items ki
        JOIN library_items li ON ki.library_id = li.id
        WHERE li.subject_id = ? AND li.deleted_at IS NULL
        ORDER BY ki.topico, ki.subtopico
        """,
        (subject_id,),
    )
    rows = await cursor.fetchall()

    topics: dict[str, list[str]] = {}
    for row in rows:
        topico = row["topico"]
        subtopico = row["subtopico"]
        if topico not in topics:
            topics[topico] = []
        if subtopico not in topics[topico]:
            topics[topico].append(subtopico)

    return {
        "topicos": [
            {"titulo": titulo, "subtopicos": subs}
            for titulo, subs in topics.items()
        ]
    }
