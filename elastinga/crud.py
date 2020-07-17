"""Operaciones CRUD."""
# -*- coding: utf-8 -*-
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from abc import ABCMeta, abstractmethod

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch_dsl import Q
from elasticsearch_dsl import Search
from elasticsearch_dsl.response import Response

from elastinga import logger
from elastinga.schemas import TwitterPosts, InstagramPosts
from elastinga.exc import IndexNotExists


class BaseSearch(metaclass=ABCMeta):
    """Clase base para operaciones de búsquedas asincrónicas."""

    def __init__(self, connection: Elasticsearch, index_name: str):

        # if not connection.indices.exists(index_name):
        #     raise IndexNotExists(index=index_name)

        self.connection = connection
        self.index_name = index_name
        super().__init__()

    @property
    def search_base(self):
        """Búsqueda con la configuración básica."""
        search = Search(using=self.connection, index=self.index_name)
        return search

    @staticmethod
    def construct_multi_field_search(  # pylint: disable=too-many-arguments
        search: Search,
        text: str,
        operator: str,
        fields: List[str],
        size: int = 5,
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None,
    ) -> Search:
        """Construye búsqueda por texto en multiples campos.

        Args:

            search: Búsqueda inicial.
            text: Texto de busquéda.
            operator: Condicional sobre los tokens del texto. Si el
                operator es `and`, entonces para que haya match, todos los
                tokens deben ser encontrados en el índice inverso. Si el
                operator es `or`, entonces para que haya match, al menos un
                token debe ser encontrado en el índice inverso.
                Ver:
                    https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-match-query.html
            size: Tamaño de la busqueda. Valor por defecto 5.
            includes: Control selectivo del campo _source.
                    Retorna solo los campos que se especifican.

            excludes: Control selectivo del campo _source.
                    Excluye los campos que se especifican.

            fields: Nombre de los fields de :class:~`elastinga.schemas.TwitterPosts`
                en donde se quiere buscar

        Returns:
            search: Search

        """

        if includes:
            search = search.source(includes=includes)

        if excludes:
            search = search.source(excludes=excludes)

        search = search.query(
            Q("multi_match", query=text, operator=operator, fields=fields)
        )

        search = search.params(size=size)

        logger.info("Query", query=search.to_dict())

        return search

    def suggest(
        self, text: str, field_name, suggestion_type, suggestion_name: str
    ) -> List[str]:
        """Corrección/sugerencia de un texto
        Args:
            field_name: Nombre del campo de referencia para sugerir.
            suggestion_type: Tipo de sugerencia de ES, `phrase` o `term`.
            suggestion_name : Identificador de la sugerencia.
            text: Texto de entrada.
        Returns:
           Lista con las opciones de sugerencia de texto. Retorna una lista
                vacía si es que no hay sugerencias.
        """
        search = self.search_base

        if suggestion_type not in ("phrase", "term"):
            raise ValueError("Parámetro `suggestion_type` debe ser `term` o `phrase`")

        if suggestion_type == "phrase":
            search = search.suggest(
                suggestion_name, text, phrase={"field": field_name, "max_errors": 3},
            )

        elif suggestion_type == "term":
            search = search.suggest(
                suggestion_name, text, term={"field": field_name, "max_errors": 3},
            )

        response = search.execute()

        if not hasattr(response, "suggest"):
            raise NotImplementedError  # TODO: Cuando el índice no tiene docs
            # entra a este error, why? que otro caso?

        suggestions = response.suggest

        # Como hicimos una sola sugerencia, la información estará
        # en el único elemeno de la lista
        suggestions = suggestions[suggestion_name][0]

        return [suggest.text for suggest in suggestions.options]

    @staticmethod
    def _hit_dsl_conversor(hit, include_meta: bool):
        return hit.to_dict() if include_meta else hit.to_dict()["_source"]

    @staticmethod
    def _hit_conversor(hit: dict, include_meta: bool):
        return hit if include_meta else hit["_source"]

    def serialize(
        self, response: Union[Response, dict], include_meta: bool
    ) -> List[dict]:
        """Serializa los resultados de una busqueda.

        Args:
            response: Resultados de la búsqueda sin procesar. Esta response
                puede ser la clase de respuesta de la librería
                `elasticsearch_dsl`, ó el diccionario de respuesta que entrega
                la librería de más bajo nivel `elasticsearch-py`
            include_meta: Si es `True`, agrega en el serializado los campos
                de `_id`, `_score`, `_index`.

        """

        conversor = getattr(
            self,
            "_hit_dsl_conversor"
            if isinstance(response, Response)
            else "_hit_conversor",
        )

        hits = response["hits"]["hits"]  # Ambas respuestas dsl y es-py

        serialized = [conversor(hit, include_meta) for hit in hits]

        return serialized

    @abstractmethod
    def _search_post(self, text, search_operator, **kwargs):
        pass

    def search_post(self, text, **kwargs):

        """Busqueda de post dado un texto"""

        posts = self._search_post(text, "and", **kwargs)

        if posts:
            return posts

        posts = self._search_post(text, "or", **kwargs)

        if posts:
            return posts

        return self.suggest_post(text, **kwargs)

    def suggest_post(self, text, **kwargs):
        """Sugerencia de post, dado un texto.

        Este método hace dos consultas. Primero, dado el texto, intenta
        corregirlo (si necesita ser corregido), si el texto fue corregido,
        realiza la query usando :meth:`elastinga.crud.TwitterSearch._search_product`

        Kwargs:
            corresponden a los kwargs
                :meth:~`elastinga.crud.BaseSearch.suggest`

        """

        suggested_text = self.suggest(
            text=text,
            field_name="text",
            suggestion_type="phrase",
            suggestion_name="post_suggest",
        )

        if suggested_text:
            return self._search_post(suggested_text[0], "or", **kwargs)
        return list()


class TwitterSearch(BaseSearch):
    """Operaciones de búsqueda para :class:`elastinga.schemas.TwitterPosts`."""

    def __init__(self, connection: Elasticsearch):
        super().__init__(connection, TwitterPosts.Index.name)

    @staticmethod
    def _filter_username_owner(
        search: Search, username_owner: Union[str, List[str]]
    ) -> Search:
        """Agrega un filter context sobre el field `username_owner`

        :class:~`elastinga.schemas.TwitterPosts`

        Args:
            search: Búsqueda a la cual agregar el filter context
            username_owner : Dueño(s) original(es) del(os) tweet(s)
        Return
            Búsqueda con el filtro.

        """
        return search.filter(
            "term" if isinstance(username_owner, str) else "terms",
            username_owner=username_owner,
        )
        # Importa la diferencia entre term y terms!

    @staticmethod
    def _filter_username_timeline(
        search: Search, username_timeline: Union[str, List[str]]
    ) -> Search:
        """Agrega un filter context sobre el field `username_timeline`

        :class:~`elastinga.schemas.TwitterPosts`

        Args:
            search: Búsqueda a la cual agregar el filter context
            username_timeline : username(s) del(os) dueño de la timeline
        Return
            Búsqueda con el filtro.

        """
        return search.filter(
            "term" if isinstance(username_timeline, str) else "terms",
            username_timeline=username_timeline,
        )

    def _search_post(  # pylint: disable=too-many-arguments
        self,
        text: str,
        search_operator: str,
        search_size: int = 5,
        username_owner: Optional[Union[str, List[str]]] = None,
        username_timeline: Optional[Union[str, List[str]]] = None,
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None,
        include_meta=False,
    ) -> List[dict]:
        """Busca un post dado un texto.

        Args:
            text : Texto de búsqueda
            username_owner : Dueño(s) original(es) del(os) tweet(s)
            username_timeline : username(s) del(os) dueño de la timeline
            include_meta : Si es True, muestra los meta fields
            de los matches.

            Los demás argumentos corresponden a los argumentos de
                :func: `~elastinga.crud.BaseSearch.construct_multi_field_search`

        Returns:
            Lista serializada de posts encontrados. Si no hay
            matches retorna una lista vacía

        """
        search_base = self.search_base

        if username_timeline is not None:
            search_base = self._filter_username_timeline(search_base, username_timeline)

        if username_owner is not None:
            search_base = self._filter_username_owner(search_base, username_owner)

        # Multi field search pues cuando se habiliten los comments, se buscará ahi tambien
        search = self.construct_multi_field_search(
            search_base,
            text,
            search_operator,
            fields=["text"],
            size=search_size,
            includes=includes,
            excludes=excludes,
        )

        response = search.execute()

        serialized = self.serialize(response, include_meta=include_meta)

        return serialized


class InstagramSearch(BaseSearch):
    def __init__(self, connection: Elasticsearch):
        super().__init__(connection, InstagramPosts.Index.name)

    @staticmethod
    def _filter_username(search: Search, username: Union[str, List[str]]) -> Search:
        """Agrega un filter context sobre el field `username`

        :class:~`elastinga.schemas.Instagram`

        Args:
            search: Búsqueda a la cual agregar el filter context
            username: Dueño del post
        Return
            Búsqueda con el filtro.

        """
        return search.filter(
            "term" if isinstance(username, str) else "terms", username=username,
        )

    def _search_post(
        self,
        text,
        search_operator: str,
        search_size: int = 5,
        username: Optional[Union[str, List[str]]] = None,
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None,
        include_meta=False,
    ) -> List[dict]:

        search_base = self.search_base

        if username:
            search_base = self._filter_username(search_base, username)

        search = self.construct_multi_field_search(
            search_base,
            text,
            search_operator,
            fields=["text"],
            size=search_size,
            includes=includes,
            excludes=excludes,
        )

        response = search.execute()

        serialized = self.serialize(response, include_meta=include_meta)

        return serialized


class FacebookSearch(BaseSearch):
    pass
