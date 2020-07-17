# -*- coding: utf-8 -*-
"""Analisis de búsqueda."""

from elasticsearch_dsl import analyzer
from elasticsearch_dsl import token_filter
from elasticsearch_dsl import tokenizer

ASCII_FILTER = token_filter(
    "ascii_filter", type="asciifolding", preserve_original=True
)

SHINGLE_FILTER = token_filter(
    "shingle_filter", type="shingle", min_shingle_size=2, max_shingle_size=2
)  # Este es importante para hacer phrase suggest!!


INDEX_ANALYZER_DESCRIPTION = analyzer(
    "index_analyzer",
    tokenizer=tokenizer(
        "auto_completado",
        "edge_ngram",
        min_gram=2,
        max_gram=15,
        token_chars=["letter", "digit", "symbol", "punctuation"],
    ),
    filter=["lowercase", ASCII_FILTER],
)

INDEX_ANALYZER_POSTS= analyzer(
    "index_analyzer",
    tokenizer=tokenizer(
        "auto_completado",
        "edge_ngram",
        min_gram=3,
        max_gram=20,
        token_chars=["letter", "digit", "symbol", "punctuation"],
    ),
    filter=["lowercase"],
)


SEARCH_ANALYZER = analyzer(
    "rebuilt_whitespace",
    tokenizer=tokenizer("whitespace", "whitespace"),
    filter=["lowercase", ASCII_FILTER],
)


SUGGESTER_ANALYZER_DESCRIPTION = analyzer(
    "rebuilt_whitespace",
    tokenizer=tokenizer("whitespace", "whitespace"),
    filter=["lowercase", SHINGLE_FILTER, ASCII_FILTER],
)

""" POST /_analyze
    {
    "analyzer": "index_analyzer",
    "text": "2 Quick Foxes."
    "token_char":["letter", "digit"]
Output
    [ Qu, Qui, Quic, Quick, Fo, Fox, Foxe, Foxes ]

Ver:
    https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-edgengram-tokenizer.html
"""
