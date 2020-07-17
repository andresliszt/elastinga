# -*- coding: utf-8 -*-
"""Definición de indices/documentos redes sociales."""
from enum import Enum

from elasticsearch import Elasticsearch
from elasticsearch_dsl.document import IndexMeta  # pylint: disable=no-name-in-module
from elasticsearch_dsl import MetaField

from elastinga import SETTINGS
from elastinga import logger
from elastinga.analyzers import INDEX_ANALYZER_DESCRIPTION
from elastinga.analyzers import INDEX_ANALYZER_POSTS
from elastinga.analyzers import SEARCH_ANALYZER
from elastinga.analyzers import SUGGESTER_ANALYZER_DESCRIPTION

from elasticsearch_dsl import (
    Document,
    InnerDoc,
    Boolean,
    Keyword,
    Nested,
    Object,
    Text,
    Integer,
    Date,
    Float,
)


class TwitterPosts(Document):
    """Definición documento Sku."""

    tweet_id = Keyword(required=True)
    """Id del tweet"""
    text = Text(analyzer=INDEX_ANALYZER_POSTS, search_analyzer=SEARCH_ANALYZER,)
    """Texto asociado al tweet"""
    username_timeline = Keyword()
    """Dueño de la cuenta de twitter donde fue encontrado el tweet"""
    tweet_url = Text()
    username_owner = Keyword()
    """Dueño original del tweet"""
    user_id = Keyword()
    is_pinned = Boolean()
    is_retweet = Boolean()
    """True o False si el tweet es retweeted"""
    replies = Integer()
    """Cantidad de veces que fue respondido el tweet"""
    retweets = Integer()
    """"Cantidad de veces que fue retweeted el tweet"""
    likes = Integer()
    """Cantidad de likes del tweet"""
    time = Date()
    """Fecha de publicación"""
    sentimiento = Float()
    entries = Object(
        dynamic="strict",
        properties={
            "hashtags": Keyword(multi=True),
            "urls": Keyword(multi=True),
            "videos": Keyword(multi=True),
            "photos": Keyword(multi=True),
        },
    )

    class Index:  # pylint: disable=too-few-public-methods
        """Index twitter."""

        name = SETTINGS.TWITTER_INDEX_NAME  # pylint: disable=no-member
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Meta:
        dynamic = MetaField("strict")

    # def to_dict_with_custom_id(self, **kwargs):
    #     """Override el método to_dict para agragar el _id field.

    #     cuando se instancia un objeto de :class: .Sku, el método
    #     to_dict no incorpora el meta field `_id`, pues este es creado al
    #     momento de guardar el dato. Agregar el `_id` field antes del guardado
    #     permite la carga de documentos con `_id` propio usando el método
    #     :meth: `elasticsearch.helpers.bulk`.

    #     Usar solo para bulk insert!

    #     """
    #     if (
    #         self.sku_id is None
    #     ):  # No se permitirán skus con id generado aleatorio
    #         raise ValueError("El campo sku_id es obligatorio")

    #     d = super().to_dict(**kwargs)
    #     d["_id"] = self.sku_id
    #     return d

    # @staticmethod
    # def build_sku_id(rut_proveedor_: int, sku: str):
    #     return "_".join((str(rut_proveedor_), str(sku)))


class InstagramComments(InnerDoc):

    post_id = Keyword(required=True)
    """Id del post de instagram"""
    text = Text(analyzer=INDEX_ANALYZER_POSTS, search_analyzer=SEARCH_ANALYZER,)
    """Texto asociado al tweet"""
    comment_user_id = Integer(required=True)
    """Id del post de instagram"""
    comment_username = Keyword()
    """Username del que comentó"""
    time = Date()
    """Fecha de publicación"""
    reported_as_spam = Boolean()
    """True o False si el post fue marcado como spam"""
    comment_user_profile_pic = Text()
    """Url foto de perfil del que comentó"""
    likes = Integer()
    """"Cantidad de likes del comentario"""
    sentimiento = Float()


class InstagramPosts(Document):

    post_id = Keyword(required=True)
    """Id del post de instagram"""
    text = Text(analyzer=INDEX_ANALYZER_POSTS, search_analyzer=SEARCH_ANALYZER)
    """Texto asociado al tweet"""
    username = Keyword()
    """Nombre del dueño del post"""
    time = Date()
    """Fecha de publicación"""
    likes = Integer()
    """Cantidad de likes del post"""
    display_url = Text()
    """url compartida"""
    thumbnail_src = Text()
    """link a photo/video"""
    is_video = Boolean()
    """True o False si es un video o no"""
    sentimiento = Float()

    comments = Nested(InstagramComments)

    def save(
        self, **kwargs
    ):  # pylint: disable=W0221 # https://github.com/PyCQA/pylint/pull/3001
        """Override el método save para generar custom id."""
        self.meta.id = self.post_id
        return super().save(**kwargs)

    class Index:  # pylint: disable=too-few-public-methods
        """Index instagram."""

        name = SETTINGS.INSTAGRAM_INDEX_NAME  # pylint: disable=no-member
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Meta:
        dynamic = MetaField("strict")


class FacebookPosts(Document):

    post_id = Integer()
    text = Text(analyzer=INDEX_ANALYZER_POSTS, search_analyzer=SEARCH_ANALYZER,)
    """Texto asociado al post"""
    time = Date()
    image = Text(multi=True)
    likes = Integer()
    comments = Integer()
    shares = Integer()
    post_url = Text()
    links = Text(multi=True)

    class Index:  # pylint: disable=too-few-public-methods
        """Index Facebook."""

        name = SETTINGS.FACEBOOK_INDEX_NAME  # pylint: disable=no-member
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Meta:
        dynamic = MetaField("strict")


def init_schema(connection: Elasticsearch, doc: IndexMeta):
    """Construye el indice y los mappings si aún no existen.

    Args:
        connection : Conexión a ES
        doc: Doc asociado al índice por crear.

    """

    if not connection.indices.exists(doc.Index.name):

        doc.init(using=connection)
    else:
        logger.warining(
            "El indice ya existe, para volver a crearlo primero se tiene que eliminar",
            indice=doc,
        )

