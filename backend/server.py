# FastAPI server definition
# Social Media Content Generator API
# Code inspired by Thu Vu's Social Media Content Generator tutorial

from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse
import asyncio
import json
import time
import os
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from agents import Agent, Runner, WebSearchTool, function_tool, trace
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Social Media Content Generator API",
    description="Generate social media content from YouTube video transcripts using AI agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:3000",
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------------------
# Step 1: Get OpenAI API Key and Configuration
# ---------------------------------------------------------------------------------------

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables")


# ---------------------------------------------------------------------------------------
# Pydantic Models for API Request/Response
# ---------------------------------------------------------------------------------------

class ContentGenerationRequest(BaseModel):
    """Request model for content generation."""
    video_id: str = Field(..., description="YouTube video ID or URL")
    platforms: List[str] = Field(
        default=["LinkedIn", "Instagram"],
        description="List of social media platforms to generate content for"
    )
    language: Optional[str] = Field(
        default="en",
        description="Language code for video transcript (e.g., 'en', 'es', 'fr')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "JZLZQVmfGn8",
                "platforms": ["LinkedIn", "Instagram", "Twitter"],
                "language": "en"
            }
        }


class PostResponse(BaseModel):
    """Response model for a single social media post."""
    platform: str
    content: str


class ContentGenerationResponse(BaseModel):
    """Response model for content generation."""
    video_id: str
    posts: List[PostResponse]
    transcript_preview: str = Field(..., description="First 200 characters of the transcript")



# ---------------------------------------------------------------------------------------
# Step 2: Define Tools for agents
# ---------------------------------------------------------------------------------------

def generate_content_core(video_transcript: str, social_media_platform: str, output_language: Optional[str] = None) -> str:
    """Core generator that calls OpenAI API and returns content as string.

    If output_language is provided, enforce that language; otherwise, auto-detect from transcript
    and write strictly in the transcript's language.
    """
    print(f"[INFO] Generating social media content for {social_media_platform} using core generator")

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Build a strong language instruction
    language_clause = (
        f"Write strictly in {output_language}. Do not switch languages or translate. "
        if output_language else
        "Detect the transcript language and write strictly in that language. Do not translate or switch languages. "
    )

    response = client.responses.create(
        model="gpt-4o",
        input=(
            "You are a social media copywriter. "
            f"Write a concise {social_media_platform} post based ONLY on the transcript below. "
            + language_clause +
            "Prefer short sentences. Avoid fluff. Keep it skimmable. "
            "Add at most 1-2 relevant hashtags when they clearly add value.\n\n"
            "Transcript:\n" + video_transcript
        ),
        max_output_tokens=500,
    )

    return response.output_text


# Tool: Generate social media content from transcript (tool wrapper)
@function_tool
def generate_content(video_transcript: str, social_media_platform: str) -> str:
    """Generate social media content from a transcript (tool wrapper)."""
    return generate_content_core(video_transcript, social_media_platform)



# ---------------------------------------------------------------------------------------
# Step 3: Define Agents
# ---------------------------------------------------------------------------------------

@dataclass
class Posts:
    platform: str
    content: str


content_writer_agent = Agent(
    name="Content Writer Agent",
instructions = (
        "You are a talented content writer agent who writes engaging, humorous, "
        "and informative highly readable content for social media platforms. "
        "You are given a video transcript and social media platforms. "
        "You need to generate social media content from the transcript "
        "using the generate_content tool for each of the given platforms. "
        "You can use the websearch tool to find relevant information "
        "on the topic and fill in some useful details if needed."
    ),
    model="gpt-4o-mini",
    tools=[
        generate_content,
        WebSearchTool()
        ],
    output_type=List[Posts],
)



# ---------------------------------------------------------------------------------------
# Step 4: Define helper
# ---------------------------------------------------------------------------------------

# Fetch the video transcript from a YouTube video using the video id
def get_video_transcript(video_id: str, language: str = "en") -> str:
    """
    Fetch the video transcript from a YouTube video using the video id.
    
    Args:
        video_id (str): The YouTube video ID
        
    Returns:
        str: The concatenated transcript text
        
    Raises:
        ValueError: If video_id is empty or invalid
        Exception: For other API-related errors
    """
    print(f"[INFO] Fetching transcript for video ID: {video_id} in language: {language} using YouTubeTranscriptApi")
    
    # Input validation
    if not video_id or not video_id.strip():
        raise ValueError("Video ID cannot be empty or None")
    
    # Clean the video ID (remove any URL parts if accidentally included)
    video_id = video_id.strip()
    if "youtube.com" in video_id or "youtu.be" in video_id:
        # Extract just the video ID from URL
        if "v=" in video_id:
            video_id = video_id.split("v=")[1].split("&")[0]
        elif "youtu.be/" in video_id:
            video_id = video_id.split("youtu.be/")[1].split("?")[0]
    
    if language is None:
        language = "en"

    try:
        # Use the new API: create instance and fetch
        ytt_api = YouTubeTranscriptApi()
        fetched_transcript = ytt_api.fetch(video_id, languages=[language])
        
        # The new API returns a FetchedTranscript object that's iterable
        # Extract text from each snippet
        transcript_text = " ".join(snippet.text for snippet in fetched_transcript)
        
        return transcript_text.strip()
        
    except Exception as e:
        # Handle different types of errors with specific messages
        if isinstance(e, ValueError):
            error_msg = f"Invalid video ID format: '{video_id}'. Please provide a valid YouTube video ID."
            print(f"ValueError: {error_msg}")
            raise ValueError(error_msg) from e
            
        elif isinstance(e, KeyError):
            error_msg = f"Video '{video_id}' not found or is private/deleted."
            print(f"KeyError: {error_msg}")
            raise KeyError(error_msg) from e
            
        elif isinstance(e, ConnectionError):
            error_msg = f"Network connection error while fetching transcript for video '{video_id}'. Please check your internet connection."
            print(f"ConnectionError: {error_msg}")
            raise ConnectionError(error_msg) from e
            
        elif isinstance(e, TimeoutError):
            error_msg = f"Request timeout while fetching transcript for video '{video_id}'. The request took too long to complete."
            print(f"TimeoutError: {error_msg}")
            raise TimeoutError(error_msg) from e
            
        elif isinstance(e, PermissionError):
            error_msg = f"Access denied for video '{video_id}'. The video may be private, restricted, or require authentication."
            print(f"PermissionError: {error_msg}")
            raise PermissionError(error_msg) from e
            
        else:
            # Handle any other unexpected errors
            error_msg = f"Unexpected error while fetching transcript for video '{video_id}': {str(e)}"
            print(f"Exception: {error_msg}")
            raise Exception(error_msg) from e


# ---------------------------------------------------------------------------------------
# Transcript cache (simple in-memory with TTL)
# ---------------------------------------------------------------------------------------

_TRANSCRIPT_CACHE: dict[tuple[str, str], tuple[str, float]] = {}
_TRANSCRIPT_TTL_SECONDS = 10 * 60  # 10 minutes


def get_transcript_cached(video_id: str, language: str = "en", refresh: bool = False) -> str:
    """
    Get transcript with simple in-memory caching to avoid refetching.
    Set refresh=True to bypass cache.
    """
    key = (video_id, language or "en")
    now = time.time()
    if not refresh and key in _TRANSCRIPT_CACHE:
        transcript, ts = _TRANSCRIPT_CACHE[key]
        if now - ts < _TRANSCRIPT_TTL_SECONDS:
            return transcript

    transcript = get_video_transcript(video_id, language)
    _TRANSCRIPT_CACHE[key] = (transcript, now)
    return transcript




# ---------------------------------------------------------------------------------------
# FastAPI Endpoints
# ---------------------------------------------------------------------------------------

@app.get("/")
async def root():
    """
    Root endpoint to verify API is running.
    
    Returns:
        dict: Welcome message and API information
    """
    return {
        "message": "Social Media Content Generator API",
        "version": "1.0.0",
        "endpoints": {
            "/generate": "POST - Generate social media content from YouTube video",
            "/health": "GET - Health check endpoint",
            "/docs": "GET - API documentation"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "api_key_configured": bool(OPENAI_API_KEY)
    }


# ---------------------------------------------------------------------------------------
# Step 5: Run the agents
# ---------------------------------------------------------------------------------------

@app.post("/generate", response_model=ContentGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_social_media_content(request: ContentGenerationRequest) -> ContentGenerationResponse:
    """
    Generate social media content from a YouTube video transcript.
    
    Args:
        request: ContentGenerationRequest containing video_id, platforms, and language
        
    Returns:
        ContentGenerationResponse: Generated content for each platform
        
    Raises:
        HTTPException: If video transcript cannot be fetched or content generation fails
    """
    try:
        logger.info(f"Received request to generate content for video: {request.video_id}")
        logger.info(f"Platforms: {request.platforms}, Language: {request.language}")
        
        # Fetch video transcript
        try:
            transcript = get_video_transcript(request.video_id, request.language)
            logger.info(f"Successfully fetched transcript (length: {len(transcript)} characters)")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid video ID: {str(e)}"
            )
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video not found: {str(e)}"
            )
        except (ConnectionError, TimeoutError) as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Network error: {str(e)}"
            )
        except PermissionError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching transcript: {str(e)}"
            )
        
        # Build platform list string
        platform_list = " and ".join([f"a {platform} post" for platform in request.platforms])
        
        # Create message for agent with language and brevity constraints
        msg = (
            f"Generate content for {platform_list} based on this video transcript. "
            f"Write strictly in {request.language}. Do not switch languages or translate. "
            f"Transcript: {transcript}"
        )
        
        input_messages = [{"role": "user", "content": msg}]
        
        # Run the agent to generate content
        try:
            with trace("Writing social media content"):
                result = await Runner.run(content_writer_agent, input_messages)
                
                # Convert dataclass Posts to Pydantic PostResponse
                posts = [
                    PostResponse(platform=post.platform, content=post.content)
                    for post in result.final_output
                ]
                
                logger.info(f"Successfully generated {len(posts)} posts")
                
                return ContentGenerationResponse(
                    video_id=request.video_id,
                    posts=posts,
                    transcript_preview=transcript[:200] + "..." if len(transcript) > 200 else transcript
                )
                
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating content: {str(e)}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        ) 


# ---------------------------------------------------------------------------------------
# Streaming (SSE) endpoint for progress updates
# ---------------------------------------------------------------------------------------

def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/generate/stream")
async def generate_social_media_content_stream(
    video_id: str = Query(..., description="YouTube video ID or URL"),
    platforms: List[str] = Query(["LinkedIn", "Instagram"], description="Platforms to generate content for"),
    language: str = Query("en", description="Transcript language code"),
):
    """
    Stream progress events as we fetch the transcript and generate content per platform.
    Events:
      - status: { stage: "starting" | "transcript_ready" | "generating" | "done" }
      - transcript: { preview: str, length: int }
      - post: { platform: str, content: str }
      - error: { message: str }
    """

    async def event_generator():
        try:
            # optional: tell the client how long to wait before retrying if disconnected
            yield "retry: 2000\n\n"

            # heartbeat task
            async def heartbeat():
                while True:
                    # SSE comment line keeps the connection alive
                    yield ": ping\n\n"
                    await asyncio.sleep(20)

            # send a starting status immediately
            yield _sse_event("status", {"stage": "starting"})

            # Fetch transcript (cached)
            try:
                transcript = get_transcript_cached(video_id, language)
            except ValueError as e:
                yield _sse_event("error", {"message": f"Invalid video ID: {str(e)}"})
                return
            except KeyError as e:
                yield _sse_event("error", {"message": f"Video not found: {str(e)}"})
                return
            except (ConnectionError, TimeoutError) as e:
                yield _sse_event("error", {"message": f"Network error: {str(e)}"})
                return
            except PermissionError as e:
                yield _sse_event("error", {"message": f"Access denied: {str(e)}"})
                return
            except Exception as e:
                yield _sse_event("error", {"message": f"Error fetching transcript: {str(e)}"})
                return

            yield _sse_event(
                "transcript",
                {
                    "preview": transcript[:200] + ("..." if len(transcript) > 200 else ""),
                    "length": len(transcript),
                },
            )
            yield _sse_event("status", {"stage": "transcript_ready"})

            # Generate per platform
            for index, platform in enumerate(platforms):
                yield _sse_event("status", {"stage": "generating", "platform": platform, "index": index})
                try:
                    # Use core function directly; run in a thread to avoid blocking the loop
                    content = await asyncio.to_thread(generate_content_core, transcript, platform, language)
                except Exception as e:
                    yield _sse_event("error", {"message": f"Error generating {platform}: {str(e)}"})
                    continue

                yield _sse_event("post", {"platform": platform, "content": content})

            yield _sse_event("status", {"stage": "done"})
            yield _sse_event("done", {})

        except Exception as e:
            # Fallback unexpected errors
            yield _sse_event("error", {"message": f"Unexpected error: {str(e)}"})

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
    }

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)


# ---------------------------------------------------------------------------------------
# Endpoint to fetch full transcript on demand
# ---------------------------------------------------------------------------------------

@app.get("/transcript")
async def get_full_transcript(
    video_id: str = Query(..., description="YouTube video ID or URL"),
    language: str = Query("en", description="Transcript language code"),
    refresh: bool = Query(False, description="Bypass cache and refetch transcript"),
):
    """Return the full transcript text for a video."""
    try:
        try:
            transcript = get_transcript_cached(video_id, language, refresh=refresh)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid video ID: {str(e)}")
        except KeyError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Video not found: {str(e)}")
        except (ConnectionError, TimeoutError) as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Network error: {str(e)}")
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching transcript: {str(e)}")

        return {
            "video_id": video_id,
            "language": language,
            "transcript": transcript,
            "length": len(transcript),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /transcript: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected server error")