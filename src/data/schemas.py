import datetime
from enum import Enum
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, field_validator
from typing import Optional



#============Enums==================
class AnimeTypeEnum(str, Enum):
    tv = "tv"
    movie = "movie"
    ova = "ova"
    special = "special"
    ona = "ona"
    music = "music"
    cm = "cm"
    pv = "pv"
    tv_special = "tv_special"

class MangaTypeEnum(str, Enum):
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

class RatingEnum(str, Enum):
    g = "g"
    pg = "pg"
    pg13 = "pg13"
    r17 = "r17"
    r = "r"
    rx = "rx"
#======================================




class MangaParams(BaseModel):                                       
    type: Optional[MangaTypeEnum] | None = Field(default=None)
    order_by: Optional[OrderByEnum] | None = Field(default=None)
    status: Optional[StatusEnum] | None = Field(default=None)
    sfw: Optional[str] | None = Field(default="true")
    min_score: Optional[float] | None = Field(default=None)
    max_score: Optional[float] | None = Field(default=None)
    start_date: Optional[str] | None = Field(default=None)           # Format: YYYY-MM-DD
    end_date: Optional[str] | None = Field(default=None)             # Format: YYYY-MM-DD
    genres: Optional[list[str]] | None = Field(default=None)
    rating: Optional[RatingEnum] | None = Field(default=None)


    @field_validator("start_date", "end_date")
    def validate_date(cls, value):
            try:
                datetime.date.fromisoformat(value)
            except ValueError:
                raise RequestValidationError("Incorrect data format, should be YYYY-MM-DD")



class AnimeParams(BaseModel):                                         # only manga or anime. Manga includes the types: Manhua, Manhwa, Light Novels, One-shot
    type: Optional[AnimeTypeEnum] | None = Field(default=None)
    order_by: Optional[OrderByEnum] | None = Field(default=None)
    status: Optional[StatusEnum] | None = Field(default=None)             # "airing" or "complete" or "upcoming"
    sfw: Optional[str] | None = Field(default="true")
    min_score: Optional[float] | None = Field(default=None)
    max_score: Optional[float] | None = Field(default=None)
    start_date: Optional[str] | None = Field(default=None)           # Format: YYYY-MM-DD
    end_date: Optional[str] | None = Field(default=None)             # Format: YYYY-MM-DD
    genres: Optional[list[str]] | None = Field(default=None)
    rating: Optional[RatingEnum] | None = Field(default=None)


    @field_validator("start_date", "end_date")
    def validate_date(cls, value):
            try:
                datetime.date.fromisoformat(value)
            except ValueError:
                raise RequestValidationError("Incorrect data format, should be YYYY-MM-DD")

