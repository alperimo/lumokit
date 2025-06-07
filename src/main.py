import asyncio
import os
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from filelock import FileLock

from api import router
from helper.custom_errors import GenericError
from settings.db import engine, get_db

###/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\###
###/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\###

## FAST API - START ##

app = FastAPI(
    title="LumoKit API",
    version="1.1.0",
    summary="A lightweight AI Toolkit Framework offering a multitude of on-chain actions and researching abilities created by Lumo Labs catering to Solana.",
)

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8000",
    "http://localhost:3000",
    "https://lumolabs.ai",
    "https://www.lumolabs.ai",
    "http://lumolabs.ai",
    "http://www.lumolabs.ai",
    "https://lumokit.ai",
    "https://www.lumokit.ai",
    "http://lumokit.ai",
    "http://www.lumokit.ai",
    "https://lumo-api.xyz",
    "https://www.lumo-api.xyz",
    "http://lumo-api.xyz",
    "http://www.lumo-api.xyz",
    "https://lumokit.netlify.app",
    "https://www.lumokit.netlify.app",
    "http://lumokit.netlify.app",
    "http://www.lumokit.netlify.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
def ping():
    return {"boop": "boop"}


## FAST API - END ##

###/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\###
###/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\###

## ERROR HANDLING - START ##


@app.exception_handler(GenericError)
async def generic_error_handler(request, exc: GenericError):
    error_detail = exc.error_detail

    return JSONResponse(content=error_detail, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log the error or customize the message
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "error": "Invalid request data",
                "detail": exc.errors(),
            }
        ),
    )


# Catch all other exceptions
@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    error_message = "Internal server error"
    error_respones = {
        "response": None,
        "error": {"errorMessage": error_message},
        "status": "failed",
    }
    return JSONResponse(content=error_respones, status_code=500)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


## ERROR HANDLING - END ##

###/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\###
###/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\###
