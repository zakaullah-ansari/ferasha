"""Catalogue search the way shoppers type.

Postgres alone, no extra service: full-text search for any-word matching and
ranking, pg_trgm for spelling slips, and a synonym list for the regional and
transliterated spellings this catalogue's words come in. Comfortably fast for
thousands of pieces; past that, GIN indexes on the document are the next step.
"""

from __future__ import annotations

import re

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramWordSimilarity,
)
from django.db.models import F, Q, Value
from django.db.models.functions import Concat, Lower, Replace

#: One spelling per garment or craft, with the ways shoppers write it.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "gharara": ("garara", "gharare"),
    "sharara": ("sarara", "sharare"),
    "lehenga": ("lehnga", "lahanga", "lehanga", "lengha", "lahenga"),
    "chikankari": ("chikan", "chikankaari", "lucknowi"),
    "zardozi": ("zardosi", "zardoshi", "zari"),
    "kurta": ("kurti", "kurtha"),
    "dupatta": ("dupata", "chunni", "chunri", "odhni"),
    "salwar": ("shalwar", "salvar"),
    "kameez": ("kamiz", "qameez", "kamees"),
    "banarasi": ("banarsi", "benarasi", "benarsi"),
    "gota": ("gotta",),
    "nikah": ("nikkah", "nikaah"),
    "walima": ("valima",),
    "palazzo": ("plazo", "palazo"),
}
_CANONICAL = {variant: canonical for canonical, variants in SYNONYMS.items() for variant in variants}

#: Words that carry no meaning in a product search; a full-text query of one alone matches nothing.
_STOPWORDS = frozenset({"a", "an", "and", "for", "in", "of", "on", "the", "to", "with"})
#: Below this many letters a fuzzy match is more likely noise than a typo.
_FUZZY_MIN_LENGTH = 4
#: pg_trgm word similarity at which a word counts as a misspelling of one in the piece.
_FUZZY_THRESHOLD = 0.45
_MAX_WORDS = 8

_CONFIG = "english"


def _readable(field: str):
    """Stored codes as the words shoppers type: raw_silk -> raw silk."""
    return Replace(F(field), Value("_"), Value(" "))


def _spellings(word: str) -> list[str]:
    canonical = _CANONICAL.get(word, word)
    return list(dict.fromkeys([word, canonical, *SYNONYMS.get(canonical, ())]))


def words_of(raw: str) -> list[str]:
    words = [word for word in re.findall(r"\w+", raw.lower()) if word not in _STOPWORDS]
    return list(dict.fromkeys(words))[:_MAX_WORDS]


def search_products(queryset, raw: str):
    """Pieces matching every word of `raw`, most relevant first.

    Relevance is attached with alias(), not annotate(): an alias never joins a
    values() GROUP BY, so facet counts over a search stay true.
    """
    words = words_of(raw)
    if not words:
        return queryset

    document = (
        SearchVector("name", weight="A", config=_CONFIG)
        + SearchVector("category__name", weight="A", config=_CONFIG)
        + SearchVector(_readable("garment_type"), weight="B", config=_CONFIG)
        + SearchVector(_readable("fabric"), weight="B", config=_CONFIG)
        + SearchVector(_readable("work_type"), weight="B", config=_CONFIG)
        + SearchVector(_readable("occasion"), weight="B", config=_CONFIG)
        + SearchVector("description", weight="C", config=_CONFIG)
    )
    # What a typo is compared with: everything but the description, whose
    # length would drown the signal.
    haystack = Lower(
        Concat(
            F("name"), Value(" "), F("category__name"), Value(" "),
            _readable("garment_type"), Value(" "), _readable("fabric"), Value(" "), _readable("work_type"),
        )
    )

    aliases = {"search_document": document}
    match = Q()
    combined = None
    fuzzy = []
    for index, word in enumerate(words):
        query = None
        for spelling in _spellings(word):
            part = SearchQuery(spelling, config=_CONFIG, search_type="plain")
            query = part if query is None else query | part
        combined = query if combined is None else combined & query
        word_match = Q(search_document=query)
        if len(word) >= _FUZZY_MIN_LENGTH:
            name = f"search_fuzzy_{index}"
            aliases[name] = TrigramWordSimilarity(Value(word), haystack)
            word_match |= Q(**{f"{name}__gte": _FUZZY_THRESHOLD})
            fuzzy.append(F(name))
        match &= word_match

    rank = SearchRank(F("search_document"), combined)
    for similarity in fuzzy:
        rank = rank + similarity * Value(0.3)
    aliases["search_rank"] = rank

    return queryset.alias(**aliases).filter(match).order_by("-search_rank", "-created_at", "pk")
