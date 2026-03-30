def parse_topics_md(content_md: str | None) -> list:
    """Parse markdown with # / ## / ### headings into a topic hierarchy."""
    if not content_md:
        return []

    topics = []
    current_topic = None
    current_subtopic = None
    current_detail = None
    detail_lines = []

    topic_counter = 0
    subtopic_counter = 0
    detail_counter = 0

    def _flush_detail():
        nonlocal detail_lines, current_detail
        if current_detail is not None:
            content = "\n".join(detail_lines).strip()
            current_detail["content_md"] = content if content else ""
            current_detail["has_content"] = bool(content)
            detail_lines = []

    for line in content_md.split("\n"):
        stripped = line.strip()

        if stripped.startswith("### "):
            _flush_detail()
            detail_counter += 1
            current_detail = {
                "title": stripped[4:].strip(),
                "id": f"{topic_counter}.{subtopic_counter}.{detail_counter}",
                "content_md": "",
                "has_content": False,
            }
            if current_subtopic is not None:
                current_subtopic["details"].append(current_detail)
            detail_lines = []

        elif stripped.startswith("## "):
            _flush_detail()
            subtopic_counter += 1
            detail_counter = 0
            current_detail = None
            current_subtopic = {
                "title": stripped[3:].strip(),
                "id": f"{topic_counter}.{subtopic_counter}",
                "details": [],
            }
            if current_topic is not None:
                current_topic["subtopics"].append(current_subtopic)

        elif stripped.startswith("# "):
            _flush_detail()
            topic_counter += 1
            subtopic_counter = 0
            detail_counter = 0
            current_detail = None
            current_subtopic = None
            current_topic = {
                "title": stripped[2:].strip(),
                "id": str(topic_counter),
                "subtopics": [],
            }
            topics.append(current_topic)

        else:
            if current_detail is not None:
                detail_lines.append(line)

    _flush_detail()
    return topics


def get_detail_content(content_md: str | None, detail_id: str) -> str | None:
    """Return the content_md of a specific detail by its hierarchical id."""
    topics = parse_topics_md(content_md)
    for topic in topics:
        for subtopic in topic["subtopics"]:
            for detail in subtopic["details"]:
                if detail["id"] == detail_id and detail["has_content"]:
                    return detail["content_md"]
    return None
