

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine(
     "sqlite+libsql:///embedded.db",
     connect_args={
         "sync_url": "libsql://coll-82fea7b566794900bb98fd7741dcfbc6-mayson.aws-ap-south-1.turso.io",
         "auth_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Nzc5ODM2NDgsInAiOnsicm9hIjp7Im5zIjpbIjAxOWRmODE1LTZhMDEtNzc1NS1hMzUxLWU3YzI3NjFiNmQwNCJdfSwicnciOnsibnMiOlsiMDE5ZGY4MTUtNmEwMS03NzU1LWEzNTEtZTdjMjc2MWI2ZDA0Il19fSwicmlkIjoiMjkzNTAxMGUtMDhmMS00MDM0LWFmNzEtZjE3NjNjNWIxYTFjIn0.YAzKf0ebyeckU0Ml9beuAjtNOEgdrlWwhgXnWvIW64zSIbV5gEN-dupJ-z9CoqbnXcfQQmyilIzF4-04mU9BDA",
     },
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()

