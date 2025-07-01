#!/usr/bin/env python3
"""
Vercel MCP Server
"""

# server.py
import os
from typing import Dict

from hirestream_client import (
    HireStreamAPIClient,
    JobApplyRequest,
    JobDetailsRequest,
    JobDetailsResponse,
    JobListingResponse,
)

import datetime
from fastmcp import FastMCP
from .mcp_adapter import build_app

# Create FastMCP server with business logic
mcp: FastMCP = FastMCP("Vercel MCP Server", stateless_http=True, json_response=True)


hirestream_client = HireStreamAPIClient(
    access_token="",
    base_api_url="https://cogent-labs.hirestream.io/api/v1",
)


@mcp.tool()
async def list_jobs() -> JobListingResponse:
    """
    Execute a swap transaction.

    Expects a SwapTransactionRequestContainer, returns a list of SwapTransactionResponse.
    """
    try:
        result: JobListingResponse = await hirestream_client.list_jobs()
        return result
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def show_job_details(
    job_details_request: JobDetailsRequest,
) -> JobDetailsResponse:
    """
    Execute a swap transaction.

    Expects a SwapTransactionRequestContainer, returns a list of SwapTransactionResponse.
    """
    try:
        result: JobDetailsResponse = await hirestream_client.show_job_details(
            job_details_request
        )
        return result
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def apply_to_job(job_apply_request: JobApplyRequest) -> Dict:
    """
    Apply to a job.

    First ask the user to upload the resume before he applies to the job.
    """
    try:
        result: JobDetailsResponse = await hirestream_client.apply_to_job(
            job_apply_request
        )
        return result
    except Exception as e:
        return [{"error": str(e)}]


# Build the FastAPI app using the adapter
app = build_app(mcp)

# For local development
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3000)
