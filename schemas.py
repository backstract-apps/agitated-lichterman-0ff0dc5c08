from pydantic import BaseModel,Field,field_validator

import datetime

import uuid

from typing import Any, Dict, List,Optional,Tuple,Union

import re

class Todos(BaseModel):
    user_id: int
    title: str
    is_completed: int
    created_at: Optional[str]=None
    updated_at: Optional[str]=None


class ReadTodos(BaseModel):
    user_id: int
    title: str
    is_completed: int
    created_at: Optional[str]=None
    updated_at: Optional[str]=None
    class Config:
        from_attributes = True


class Users(BaseModel):
    email: str
    password: str
    created_at: Optional[str]=None


class ReadUsers(BaseModel):
    email: str
    password: str
    created_at: Optional[str]=None
    class Config:
        from_attributes = True




class PostTodos(BaseModel):
    user_id: Union[int, float] = Field(...)
    title: str = Field(..., max_length=500)
    is_completed: Union[int, float] = Field(...)
    created_at: Optional[str]=None
    updated_at: Optional[str]=None

    class Config:
        from_attributes = True



class PutTodosId(BaseModel):
    id: str = Field(..., max_length=100)
    user_id: Union[int, float] = Field(...)
    title: str = Field(..., max_length=500)
    is_completed: Union[int, float] = Field(...)
    created_at: Optional[str]=None
    updated_at: Optional[str]=None

    class Config:
        from_attributes = True



class PostPlatformAuthPackageMaysonAuthUserRegister(BaseModel):
    email: str = Field(..., max_length=100)
    password: str = Field(..., max_length=100)

    class Config:
        from_attributes = True



class PostUsers(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=255)
    created_at: Optional[str]=None

    class Config:
        from_attributes = True



class PutUsersId(BaseModel):
    id: str = Field(..., max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=255)
    created_at: Optional[str]=None

    class Config:
        from_attributes = True



class PostPlatformAuthPackageMaysonAuthUserLogin(BaseModel):
    email: str = Field(..., max_length=100)
    password: str = Field(..., max_length=100)

    class Config:
        from_attributes = True



# Query Parameter Validation Schemas

class GetTodosIdQueryParams(BaseModel):
    """Query parameter validation for get_todos_id"""
    id: int = Field(..., ge=1, description="Id")

    class Config:
        populate_by_name = True


class GetUsersIdQueryParams(BaseModel):
    """Query parameter validation for get_users_id"""
    id: int = Field(..., ge=1, description="Id")

    class Config:
        populate_by_name = True


class DeleteUsersIdQueryParams(BaseModel):
    """Query parameter validation for delete_users_id"""
    id: int = Field(..., ge=1, description="Id")

    class Config:
        populate_by_name = True


class DeleteTodosIdQueryParams(BaseModel):
    """Query parameter validation for delete_todos_id"""
    id: int = Field(..., ge=1, description="Id")

    class Config:
        populate_by_name = True
