from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from Logs import Logger
import logging

# Logging for debugging
schemas_logger = Logger(logger_name='schemas_logger', log_file='schemas.log').get_logger()

"""
    q: Optional[str]                    # Free search


    min_score: Optional[float]
    max_score: Optional[float]
    genres_exclude: Optional[int]
    order_by: Optional[str]             # "mal_id", "title",  "start_date", "end_date", "episodes", "score", "scored_by", "rank", "popularity", "members", "favorites"
    sort: Optional[str]                 # "desc" or "asc"
    producers: Optional[int]
    start_date: Optional[str]           # Format: YYYY-MM-DD
    end_date: Optional[str]             # Format: YYYY-MM-DD

    genres: Optional[list[int]] = Field(default=None)
    rating: Optional[str] = Field(default=None)
    
"""


class SubjectEnum(str, Enum):
    anime = "anime"
    manga = "manga"

class TypeAnimeEnum(str, Enum):
    tv = "tv"
    movie = "movie"
    ova = "ova"
    special = "special"
    ona = "ona"
    music = "music"
    cm = "cm"
    pv = "pv"
    tv_special = "tv_special"
    
class TypeMangaEnum(str, Enum):
    manga = "manga"
    novel = "novel"
    lightnovel = "lightnovel"
    oneshot = "oneshot"
    doujin = "doujin"
    manhwa = "manhwa"
    manhua = "manhua"

class OrderByEnum(str, Enum):
    mal_id = "mal_id"
    title = "title"
    start_date = "start_date"
    end_date = "end_date"
    episodes = "episodes"
    score = "score"
    scored_by = "scored_by"
    rank = "rank"
    popularity = "popularity"
    members= "members"
    favorites = "favorites"

class StatusEnum(str, Enum):
    airing = "airing"
    complete = "complete"
    upcoming = "upcoming"





class LayerOneParameters(BaseModel):
    subject: SubjectEnum                                            # only manga or anime. Manga includes the types: Manhua, Manhwa, Light Novels, One-shot
    type: Optional[TypeAnimeEnum] = Field(default=None)
    order_by: Optional[OrderByEnum] = Field(default=None)
    status: Optional[str] = Field(default=None)             # "airing" or "complete" or "upcoming"
    sfw: Optional[str] = Field(default="true")










# - Comment out the field validators cuz they look messy. Implementing ENUM instead
"""
    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value):

        valid_subjects = {"anime", "manga"}
        if value.lower() not in valid_subjects:
            schemas_logger.warning(f"Subject Validator: Rejected {value}| Raising Value Error")
            raise ValueError(f"Invalid subject: {value}")
            # Raises ValueError to halt request. Valid subject is required
        return value
    
    @field_validator("order_by")
    @classmethod
    def validate_order_by(cls, value):
        valid_order_by = {"mal_id", "title", "start_date", "end_date", "episodes", "score", "scored_by", "rank", "popularity", "members", "favorites"}
        if value.lower() not in valid_order_by:
            schemas_logger.warning(f"Order_By Validator: Rejected {value} -> {None}")
            return None
            # Raises ValueError to halt request. Valid subject is required
        return value


    # Other fields that are optional does not raise ValueError
    # Only converted to <None> to exclude in parameters

    @field_validator("type")
    @classmethod
    def validate_type(cls, value):
        if value is None:
            schemas_logger.info(f"<None> type Received")
            return None

        valid_types = {"tv", "movie", "ova", "special", "ona", "music", "cm", "pv", "tv_special"} 
        if value.lower() not in valid_types:
            schemas_logger.warning(f"Type Validator: Rejected {value} -> {None}")
            return None
            # Change rejected value into <None> then exclude all <None> in the parameters
        return value
    
    # Same for the other validators below

    
    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value):
        if value is None:
            schemas_logger.info(f"<None> rating Received")
            return None

        valid_ratings = {"g", "pg", "pg13", "r17", "r", "rx"}
        if value.lower() not in valid_ratings:
            schemas_logger.warning(f"Rating Validator: Rejected {value} -> {None}")
            return None
        return value
    
    

    @field_validator("genres")
    @classmethod
    def validate_genres(cls, value: list):
        if value is None:
            schemas_logger.info(f"<None> genres Received")
            return None

        if len(value) <= 1 and value[0] == 0:
            schemas_logger.warning(f"Genres Validator: Rejected {value} -> {None}")
            return None
        return value
    

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        if value is None:
            schemas_logger.info(f"<None> status Received")
            return None

        valid_ratings = {"airing", "complete", "upcoming"}
        if value.lower() not in valid_ratings:
            schemas_logger.warning(f"Status Validator: Rejected {value} -> {None}")
            return None
        return value

"""