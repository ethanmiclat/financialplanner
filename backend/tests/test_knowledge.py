"""Content integrity for the knowledge base — every link resolves, nothing is a stub,
and the glossary is extended rather than duplicated."""

import content
import knowledge as K
import qa
import scenario


def test_shape_and_size():
    assert len(K.ENTRIES) >= 80
    assert len(K.DECLINES) >= 8
    for key, e in K.ENTRIES.items():
        for field in ("question", "topic", "level", "keywords", "summary", "detail", "related", "glossary_terms"):
            assert field in e, (key, field)
        assert e["level"] in ("basic", "intermediate"), key
        assert e["topic"] in K.TOPIC_ORDER, key
        assert len(e["keywords"]) >= 5, key


def test_no_stubs():
    for key, e in K.ENTRIES.items():
        assert len(e["detail"]) > 80, key
        assert e["summary"] and e["question"].endswith("?"), key


def test_links_resolve():
    for key, e in K.ENTRIES.items():
        for r in e["related"]:
            assert r in K.ENTRIES, (key, r)
        for g in e["glossary_terms"]:
            assert g in content.GLOSSARY, (key, g)
    for did, d in K.DECLINES.items():
        assert d["kind"] in ("design", "capability"), did
        for r in d["redirect"]:
            assert r in K.ENTRIES or r in qa.QUESTIONS, (did, r)


def test_no_duplicate_questions_or_id_collisions():
    questions = [e["question"] for e in K.ENTRIES.values()]
    assert len(questions) == len(set(questions))
    ids = set(K.ENTRIES) | set(K.DECLINES)
    assert not (ids & set(qa.QUESTIONS)), ids & set(qa.QUESTIONS)
    assert not (ids & set(scenario.SCENARIOS)), ids & set(scenario.SCENARIOS)


def test_entries_extend_the_glossary_rather_than_repeat_it():
    """An entry that links a glossary term must say more than the term's one-liner."""
    for key, e in K.ENTRIES.items():
        for g in e["glossary_terms"]:
            assert content.GLOSSARY[g]["short"] not in e["detail"], (key, g)


def test_index_is_grouped_and_complete():
    idx = K.index()
    assert [t["topic"] for t in idx] == K.TOPIC_ORDER
    assert sum(len(t["entries"]) for t in idx) == len(K.ENTRIES)
