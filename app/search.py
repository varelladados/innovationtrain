"""Busca em memória sobre o índice — stdlib puro, sem motor de busca externo.
Score simples: título x5, nome de arquivo x3, frontmatter x2, corpo x1.
"""
import re

WORD_RE = re.compile(r"\S+")


def _count(haystack: str, needle: str) -> int:
    if not haystack or not needle:
        return 0
    return haystack.lower().count(needle.lower())


def _snippet(text: str, needle: str, width=90) -> str:
    if not text or not needle:
        return (text or "")[:width]
    idx = text.lower().find(needle.lower())
    if idx == -1:
        return text[:width]
    start = max(0, idx - width // 2)
    end = min(len(text), idx + len(needle) + width // 2)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end] + suffix


def search(entries, text_cache, query: str, limit=30):
    query = (query or "").strip()
    if not query:
        return []
    terms = WORD_RE.findall(query)
    if not terms:
        return []

    results = []
    for entry in entries:
        path = entry["path"]
        title = entry.get("title", "")
        name = path.rsplit("/", 1)[-1]
        frontmatter_text = " ".join(f"{k} {v}" for k, v in entry.get("frontmatter", {}).items())
        body = text_cache.get(path, "")

        total_score = 0
        matched_all = True
        for term in terms:
            score = (
                _count(title, term) * 5
                + _count(name, term) * 3
                + _count(frontmatter_text, term) * 2
                + _count(body, term) * 1
            )
            if score == 0:
                matched_all = False
                break
            total_score += score

        if matched_all and total_score > 0:
            results.append({
                "path": path,
                "type": entry["type"],
                "title": title,
                "score": total_score,
                "snippet": _snippet(body, terms[0]),
                "processed": entry.get("processed", False),
                "is_stub": entry.get("is_stub", False),
            })

    results.sort(key=lambda r: -r["score"])
    return results[:limit]
