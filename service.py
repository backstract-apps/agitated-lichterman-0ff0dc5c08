from sqlalchemy.orm import Session, aliased
from database import SessionLocal
from sqlalchemy import and_, or_
from typing import *
from loguru import logger
from fastapi import Request, UploadFile, HTTPException, status
from fastapi.responses import RedirectResponse, StreamingResponse
import models, schemas
import boto3
import jwt
from datetime import datetime, timezone, date, time
import requests
import math
import os
import json
import random
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from agents import (
    Agent,
    Runner,
    RunConfig,
    ModelSettings,
    InputGuardrail,
    OutputGuardrail,
)
import agent_session_store as store


load_dotenv()


def convert_to_datetime(date_string):
    if date_string is None:
        return datetime.now()
    if not date_string.strip():
        return datetime.now()
    if "T" in date_string:
        try:
            return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        except ValueError:
            date_part = date_string.split("T")[0]
            try:
                return datetime.strptime(date_part, "%Y-%m-%d")
            except ValueError:
                return datetime.now()
    else:
        # Try to determine format based on first segment
        parts = date_string.split("-")
        if len(parts[0]) == 4:
            # Likely YYYY-MM-DD format
            try:
                return datetime.strptime(date_string, "%Y-%m-%d")
            except ValueError:
                return datetime.now()

        # Try DD-MM-YYYY format
        try:
            return datetime.strptime(date_string, "%d-%m-%Y")
        except ValueError:
            return datetime.now()

        # Fallback: try YYYY-MM-DD if not already tried
        if len(parts[0]) != 4:
            try:
                return datetime.strptime(date_string, "%Y-%m-%d")
            except ValueError:
                return datetime.now()

        return datetime.now()


class SessionStoreAdapter:

    def load_session(self, session_id: str) -> dict:
        return store.load_session_memory(session_id)

    def save_session(self, session_id: str, data: dict) -> None:
        store.save_session_memory(session_id, data)


_memory_adapter = SessionStoreAdapter()


async def agent_create_session(body: str):
    """Start a new chat session."""
    meta = store.create_session(title=body, session_id=body)
    return meta


async def agent_get_history(session_id: str):
    """Return the human-readable message history for a session."""
    if not store.get_session(session_id):
        raise HTTPException(404, "Session not found")
    messages = store.get_chat_history(session_id)
    return {"session_id": session_id, "messages": messages}


async def _agent_generate_title(
    first_message: str, run_config: RunConfig, agent: Agent
) -> str:
    """Ask the LLM for a short 4-word session title from the first user message."""
    try:
        result = await asyncio.wait_for(
            Runner.run(
                agent,
                f"Give a 4-word title (no quotes, no punctuation) that summarises this message: {first_message[:300]}",
                run_config=run_config,
            ),
            timeout=15,
        )
        title = str(result.final_output).strip()[:60]
        return title if title else first_message[:40]
    except Exception:
        return first_message[:40]


async def get_todos(
    request: Request,
    db: Session,
):

    query = db.query(models.Todos)

    todos_all = query.all()
    todos_all = (
        [new_data.to_dict() for new_data in todos_all] if todos_all else todos_all
    )

    res = {
        "status": 200,
        "message": "This is the default message.",
        "data": {"todos_all": todos_all},
    }
    return res


async def get_todos_id(
    request: Request,
    db: Session,
    id: Union[int, float],
):

    query = db.query(models.Todos)
    query = query.filter(and_(models.Todos.id == id))

    todos_one = query.first()

    todos_one = (
        (todos_one.to_dict() if hasattr(todos_one, "to_dict") else vars(todos_one))
        if todos_one
        else todos_one
    )

    res = {
        "status": 200,
        "message": "This is the default message.",
        "data": {"todos_one": todos_one},
    }
    return res


async def post_todos(
    request: Request,
    db: Session,
    raw_data: schemas.PostTodos,
):
    user_id: Union[int, float] = raw_data.user_id
    title: str = raw_data.title
    is_completed: Union[int, float] = raw_data.is_completed
    created_at: str = convert_to_datetime(raw_data.created_at)
    updated_at: str = convert_to_datetime(raw_data.updated_at)

    record_to_be_added = {
        "title": title,
        "user_id": user_id,
        "created_at": created_at,
        "updated_at": updated_at,
        "is_completed": is_completed,
    }
    new_todos = models.Todos(**record_to_be_added)
    db.add(new_todos)
    db.commit()
    db.refresh(new_todos)
    todos_inserted_record = new_todos.to_dict()

    res = {
        "status": 200,
        "message": "This is the default message.",
        "data": {"todos_inserted_record": todos_inserted_record},
    }
    return res


async def put_todos_id(
    request: Request,
    db: Session,
    raw_data: schemas.PutTodosId,
):
    id: str = raw_data.id
    user_id: Union[int, float] = raw_data.user_id
    title: str = raw_data.title
    is_completed: Union[int, float] = raw_data.is_completed
    created_at: str = convert_to_datetime(raw_data.created_at)
    updated_at: str = convert_to_datetime(raw_data.updated_at)

    query = db.query(models.Todos)
    query = query.filter(and_(models.Todos.id == id))
    todos_edited_record = query.first()

    if todos_edited_record:
        for key, value in {
            "id": id,
            "title": title,
            "user_id": user_id,
            "created_at": created_at,
            "updated_at": updated_at,
            "is_completed": is_completed,
        }.items():
            setattr(todos_edited_record, key, value)

        db.commit()

        db.refresh(todos_edited_record)

        todos_edited_record = (
            todos_edited_record.to_dict()
            if hasattr(todos_edited_record, "to_dict")
            else vars(todos_edited_record)
        )

    res = {
        "status": 200,
        "message": "This is the default message.",
        "data": {"todos_edited_record": todos_edited_record},
    }
    return res


async def get_platform_auth_package_mayson_sso_auth_me(
    request: Request,
    db: Session,
):

    # get auth header

    try:
        auth_header = request.headers.get("authorization")
        auth_header = (
            auth_header[7:]
            if auth_header and auth_header.lower().startswith("bearer ")
            else auth_header
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

    import jwt

    try:
        user_profile = jwt.decode(
            auth_header,
            """kTV8IXOqGjQgCqkjpbW1xoqeHSkARTVX9y_IseHIWIA=""",
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")

    # profile_data = user_profile["data"]

    try:
        profile_data = user_profile["data"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

    res = {
        "status": 200,
        "message": "The request has been successfully processed",
        "data": {"user_profile": profile_data},
    }
    return res


async def get_users(
    request: Request,
    db: Session,
):

    query = db.query(models.Users)

    users_all = query.all()
    users_all = (
        [new_data.to_dict() for new_data in users_all] if users_all else users_all
    )

    res = {
        "status": 200,
        "message": "This is the default message.",
        "data": {"users_all": users_all},
    }
    return res


async def get_platform_auth_package_mayson_sso_auth_callback(
    request: Request,
    db: Session,
):

    user_identity: str = "i"

    user_password: str = "top_secret_area_51"

    from passlib.hash import md5_crypt

    encrypt_pass = md5_crypt.hash(user_password)

    # get user email from request

    try:
        param_obj = dict(request.query_params)

        not_found_page = "https://mayson.dev/not-found"
        user_identity = param_obj.get(
            "user_email", "no-user-identity-received-from-backend"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

    query = db.query(models.Users)
    query = query.filter(and_(models.Users.email == user_identity))
    has_a_record = query.count() > 0

    if has_a_record:
        pass

    else:

        record_to_be_added = {"email": user_identity, "password": encrypt_pass}
        new_users = models.Users(**record_to_be_added)
        db.add(new_users)
        db.commit()
        db.refresh(new_users)
        post_user_record = new_users.to_dict()

    query = db.query(models.Users)
    query = query.filter(and_(models.Users.email == user_identity))

    user_record = query.first()

    user_record = (
        (
            user_record.to_dict()
            if hasattr(user_record, "to_dict")
            else vars(user_record)
        )
        if user_record
        else user_record
    )

    import jwt
    from datetime import timezone

    secret_key = """kTV8IXOqGjQgCqkjpbW1xoqeHSkARTVX9y_IseHIWIA="""
    bs_jwt_payload = {
        "exp": int(datetime.now(timezone.utc).timestamp() + 86400),
        "data": user_record,
    }

    generated_jwt = jwt.encode(bs_jwt_payload, secret_key, algorithm="HS256")

    # define client

    try:
        request_token = generated_jwt or "no-generated-jwt"
        request_provider = param_obj.get("provider", "no-provider-from-backend")
        final_url = f'{param_obj.get("frontend-redirect", not_found_page)}?token={request_token}&provider={request_provider}'

        return RedirectResponse(url=final_url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

    res = {
        "status": 200,
        "message": "The request has been successfully processed",
        "data": {"message": "success_response"},
    }
    return res


async def post_platform_auth_package_mayson_auth_user_register(
    request: Request,
    db: Session,
    raw_data: schemas.PostPlatformAuthPackageMaysonAuthUserRegister,
):
    email: str = raw_data.email
    password: str = raw_data.password

    query = db.query(models.Users)
    query = query.filter(and_(models.Users.email == email))

    existing_record = query.first()

    existing_record = (
        (
            existing_record.to_dict()
            if hasattr(existing_record, "to_dict")
            else vars(existing_record)
        )
        if existing_record
        else existing_record
    )

    if existing_record:

        raise HTTPException(status_code=400, detail="User already exists.")
    else:
        pass

    from passlib.hash import md5_crypt

    encrypt_pass = md5_crypt.hash(password)

    record_to_be_added = {"email": email, "password": encrypt_pass}
    new_users = models.Users(**record_to_be_added)
    db.add(new_users)
    db.commit()
    db.refresh(new_users)
    post_user_record = new_users.to_dict()

    res = {"status": 200, "message": "User registered successfully", "data": {}}
    return res


async def get_users_id(
    request: Request,
    db: Session,
    id: Union[int, float],
):

    query = db.query(models.Users)
    query = query.filter(and_(models.Users.id == id))

    users_one = query.first()

    users_one = (
        (users_one.to_dict() if hasattr(users_one, "to_dict") else vars(users_one))
        if users_one
        else users_one
    )

    res = {
        "status": 200,
        "message": "This is the default message.",
        "data": {"users_one": users_one},
    }
    return res


async def post_users(
    request: Request,
    db: Session,
    raw_data: schemas.PostUsers,
):
    email: str = raw_data.email
    password: str = raw_data.password
    created_at: str = convert_to_datetime(raw_data.created_at)

    record_to_be_added = {
        "email": email,
        "password": password,
        "created_at": created_at,
    }
    new_users = models.Users(**record_to_be_added)
    db.add(new_users)
    db.commit()
    db.refresh(new_users)
    users_inserted_record = new_users.to_dict()

    res = {
        "status": 200,
        "message": "This is the default message.",
        "data": {"users_inserted_record": users_inserted_record},
    }
    return res


async def put_users_id(
    request: Request,
    db: Session,
    raw_data: schemas.PutUsersId,
):
    id: str = raw_data.id
    email: str = raw_data.email
    password: str = raw_data.password
    created_at: str = convert_to_datetime(raw_data.created_at)

    query = db.query(models.Users)
    query = query.filter(and_(models.Users.id == id))
    users_edited_record = query.first()

    if users_edited_record:
        for key, value in {
            "id": id,
            "email": email,
            "password": password,
            "created_at": created_at,
        }.items():
            setattr(users_edited_record, key, value)

        db.commit()

        db.refresh(users_edited_record)

        users_edited_record = (
            users_edited_record.to_dict()
            if hasattr(users_edited_record, "to_dict")
            else vars(users_edited_record)
        )

    res = {
        "status": 200,
        "message": "This is the default message.",
        "data": {"users_edited_record": users_edited_record},
    }
    return res


async def delete_users_id(
    request: Request,
    db: Session,
    id: Union[int, float],
):

    query = db.query(models.Users)
    query = query.filter(and_(models.Users.id == id))

    record_to_delete = query.first()
    if record_to_delete:
        db.delete(record_to_delete)
        db.commit()
        users_deleted = record_to_delete.to_dict()
    else:
        users_deleted = record_to_delete

    res = {
        "status": 200,
        "message": "This is the default message.",
        "data": {"users_deleted": users_deleted},
    }
    return res


async def post_platform_auth_package_mayson_auth_user_login(
    request: Request,
    db: Session,
    raw_data: schemas.PostPlatformAuthPackageMaysonAuthUserLogin,
):
    email: str = raw_data.email
    password: str = raw_data.password

    query = db.query(models.Users)
    query = query.filter(and_(models.Users.email == email))

    oneRecord = query.first()

    oneRecord = (
        (oneRecord.to_dict() if hasattr(oneRecord, "to_dict") else vars(oneRecord))
        if oneRecord
        else oneRecord
    )

    if oneRecord:
        from passlib.hash import md5_crypt

        password_hash_mayson = oneRecord["password"]
        password_valid = md5_crypt.verify(password, password_hash_mayson)
        if password_valid:
            validated_password = True
        else:
            validated_password = False
    else:
        validated_password = False

    login_status: str = "Login initiated"

    if validated_password:

        login_status = "Login success"

    else:

        raise HTTPException(status_code=401, detail="Bad credentials.")

    query = db.query(models.Users)
    query = query.filter(and_(models.Users.email == email))

    user_record = query.first()

    user_record = (
        (
            user_record.to_dict()
            if hasattr(user_record, "to_dict")
            else vars(user_record)
        )
        if user_record
        else user_record
    )

    import jwt
    from datetime import timezone

    secret_key = """kTV8IXOqGjQgCqkjpbW1xoqeHSkARTVX9y_IseHIWIA="""
    bs_jwt_payload = {
        "exp": int(datetime.now(timezone.utc).timestamp() + 86400),
        "data": user_record,
    }

    generated_jwt = jwt.encode(bs_jwt_payload, secret_key, algorithm="HS256")

    login_status = "Login successful"

    res = {
        "status": 200,
        "message": "Login successful",
        "data": {"jwt": generated_jwt, "login_status": login_status},
    }
    return res


async def delete_todos_id(
    request: Request,
    db: Session,
    id: Union[int, float],
):

    query = db.query(models.Todos)
    query = query.filter(and_(models.Todos.id == id))

    record_to_delete = query.first()
    if record_to_delete:
        db.delete(record_to_delete)
        db.commit()
        todos_deleted = record_to_delete.to_dict()
    else:
        todos_deleted = record_to_delete

    res = {
        "status": 200,
        "message": "This is the default message.",
        "data": {"todos_deleted": todos_deleted},
    }
    return res


async def get_platform_auth_package_mayson_sso_auth_login_google(
    request: Request,
    db: Session,
):

    # define client

    try:
        import httpx

        async def google_login():
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": "Bearer v4.public.eyJlbWFpbF9pZCI6ICJzaGl2YW00Mzg2ODdAeW9wbWFpbC5jb20iLCAidXNlcl9pZCI6ICI0YmE4ZDMyZDdhMDM0OGE5ODdhYmNmZTIzZDU3YmYyYyIsICJvcmdfaWQiOiAiTkEiLCAic3RhdGUiOiAic2lnbnVwIiwgInJvbGVfbmFtZSI6ICJOQSIsICJyb2xlX2lkIjogIk5BIiwgInBsYW5faWQiOiAiMTEzIiwgImFjY291bnRfdmVyaWZpZWQiOiAiMSIsICJhY2NvdW50X3N0YXR1cyI6ICIwIiwgInVzZXJfbmFtZSI6ICI0YmE4ZDMyZDdhMDM0OGE5ODdhYmNmZTIzZDU3YmYyYyIsICJzaWdudXBfcXVlc3Rpb24iOiAwLCAidG9rZW5fbGltaXQiOiBudWxsLCAidG9rZW5fdHlwZSI6ICJhY2Nlc3MiLCAiZXhwIjogMTc3ODU4ODQ3NCwgImV4cGlyeV90aW1lIjogMTc3ODU4ODQ3NH1m_5shKJT9pRrKKz-Z0wy0JrX8lrQyRF3Q6gK5OQV8uLSbEgWFPtkEZccpd-4inRul57FJIm20a7SOG-XA-1AE",
                    "Content-Type": "application/json",
                }

                res = await client.get(
                    "https://api-release.beemerbenzbentley.site/sigma/api/v1/sso/auth/google/login?collection_id=coll_82fea7b566794900bb98fd7741dcfbc6",
                    headers=headers,
                )

            res.raise_for_status()

            try:
                response_obj = dict(res.json())
                final_url = response_obj.get("value")
                return final_url
            except Exception as e:
                return f"https://mayson.dev/not-found?reason={str(e)}"

        return RedirectResponse(url=await google_login())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

    res = {
        "status": 200,
        "message": "The request has been successfully processed",
        "data": {"message": "success_response"},
    }
    return res
