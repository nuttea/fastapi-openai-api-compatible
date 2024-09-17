import async_timeout
import asyncio
import json
import time
import os
from typing import Optional, List

from openai import OpenAI

import google.auth
import google.auth.transport.requests

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security.api_key import APIKeyHeader
#from fastapi.responses import StreamingResponse
from starlette.responses import StreamingResponse

from routers import ChatCompletionRequest, Message

PROJECT_ID = os.getenv("PROJECT_ID", "nuttee-lab-00")
LOCATION = os.getenv("LOCATION", "us-central1")
GENERATION_TIMEOUT_SEC = 1800

BASE_URL = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/openapi"
if os.getenv("BASE_URL"):
    BASE_URL = os.getenv("BASE_URL")

# Programmatically get an access token
creds, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
auth_req = google.auth.transport.requests.Request()
creds.refresh(auth_req)

API_KEY = os.getenv("API_KEY", "1234")  # Replace with your actual API key
API_KEY_NAME = "Authorization"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

router = APIRouter(
    prefix="/vertex-ai",
    tags=["vertex-ai"],
    responses={404: {"description": "Not found"}},
)

client = OpenAI(
    base_url = BASE_URL,
    api_key = creds.token
    )

def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verifies the API key provided in the request header.

    Args:
        api_key (str, optional): The API key provided in the request header. Defaults to Depends(api_key_header).

    Raises:
        HTTPException: If the API key is missing or invalid.
    """
    if api_key is None:
        print("API key is missing")
        raise HTTPException(status_code=403, detail="API key is missing")
    if api_key != f"Bearer {API_KEY}":
        print(f"Invalid API key: {api_key}")
        raise HTTPException(status_code=403, detail="Could not validate API key")
    print(f"API key validated: {api_key}")

async def _resp_async_generator(messages: List[Message], model: str, max_tokens: int, temperature: float):
    """Asynchronous generator for streaming chat completions.

    Args:
        messages (List[Message]): The list of messages in the conversation.
        model (str): The ID of the model to use for the chat completion.
        max_tokens (int): The maximum number of tokens to generate.
        temperature (float): The temperature to use for the chat completion.

    Yields:
        str: A string containing a chunk of the streaming response.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": m.role, "content": m.content} for m in messages],
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
    )

    usage = None

    # Iterate over the response synchronously
    for chunk in response:
        #print(f"chunk: {chunk}")
        if chunk.usage is not None:
            #print(f"######### found_usage: {chunk.usage}")
            usage = {
                "prompt_tokens": chunk.usage.prompt_tokens,
                "completion_tokens": chunk.usage.completion_tokens,
                "total_tokens": chunk.usage.total_tokens
            }
        if chunk.choices[0].delta.content is not None:
            #print(f"!!!!!!!!! found_content: {chunk.choices[0].delta.content}")
            current_response = {
                "id": chunk.id,
                "object": chunk.object,
                "created": chunk.created,
                "model": chunk.model,
                "system_fingerprint": chunk.system_fingerprint,
                "usage": usage,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": chunk.choices[0].delta.content,
                            "function_call": None,
                            "refusal": None,
                            "role": "assistant",
                            "tool_calls": None
                        },
                        "finish_reason": chunk.choices[0].finish_reason,
                        "logprobs": None,
                    }
                ]
            }
            #last_chunk = chunk
        #print(f"raw_data: {current_response}")
        yield f"data: {json.dumps(current_response)}\n\n"
        #print(f"data: {json.dumps(chunk)}")
        #yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.200)

    #print("data: [DONE]")
    yield "data: [DONE]\n\n"

@router.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: ChatCompletionRequest):
    """Creates a chat completion using the OpenAI API.

    Args:
        request (ChatCompletionRequest): The request body for the chat completion.

    Returns:
        Union[StreamingResponse, ChatCompletion]: A StreamingResponse if the request is for a streaming response, otherwise a ChatCompletion object.

    Raises:
        HTTPException: If no messages are provided in the request or if there is an error processing the request.
    """
    if request.messages:
        print(f"Request: {request}")
        if request.stream:
            return StreamingResponse(
                _resp_async_generator(
                    messages=request.messages,
                    model=request.model,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                ), media_type="text/event-stream"
            )
        else:
            response = client.chat.completions.create(
                model=request.model,
                messages=[{"role": m.role, "content": m.content} for m in request.messages],
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
            print(f"Response: {response}")
            return response
    else:
        return HTTPException(status_code=400, detail="No messages provided")

@router.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    """
    List and describe the various models available in the API.

    Returns:
        dict: A dictionary containing a list of models with their details.
              Each model has the following attributes:
                - id (str): The identifier of the model.
                - object (str): The type of object, which is always "model".
                - created (int): The timestamp of when the model was created.
                - owned_by (str): The owner of the model.
    """
    models = [
        {
            "id": "google/gemini-1.5-flash-001",
            "object": "model",
            "created": 1686935002,
            "owned_by": "google"
        },
        {
            "id": "google/gemini-1.5-pro-001",
            "object": "model",
            "created": 1686935002,
            "owned_by": "google"
        }
    ]
    return {"object": "list", "data": models}
