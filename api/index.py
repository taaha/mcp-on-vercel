#!/usr/bin/env python3
"""
Vercel MCP Server
"""
import json
import logging
import os
import tempfile
import traceback

import gdown

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing_extensions import Dict, List, Optional, Union


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

load_dotenv()
BASE_API_URL = os.getenv("BASE_API_URL")


# ------------------------------
# BaseModel Definitions
# ------------------------------


class Job(BaseModel):
    id: int
    uuid: str = Field(
        description="The UUID of the job. This UUID can be used further to get details about the job."
    )
    title: str
    department: str
    location: str
    positions: int
    is_remote: bool
    priority: int


class Department(BaseModel):
    title: str
    id: int
    job_count: int


class JobListingResponse(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[Job]
    departments: List[Department]


class JobDetailsRequest(BaseModel):
    job_uuid: str = Field(description="The UUID of the job to get details for")


class JobDetailsResponse(BaseModel):
    job: Job
    departments: List[Department]


class Skill(BaseModel):
    id: int
    title: str


class Education(BaseModel):
    org: str
    degree: str
    start_date: str
    end_date: str
    current_degree: bool


class Employment(BaseModel):
    org: str
    designation: str
    start_date: str
    end_date: str
    current_job: bool


class ResumeData(BaseModel):
    url: str
    temp_url: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    tagged_education: Optional[List[Education]] = None
    education_raw_txt: Optional[str] = None
    skills: Optional[List[Skill]] = None
    tagged_employment: Optional[List[Employment]] = None
    employment_raw_txt: Optional[str] = None
    parsed_json_url: Optional[str] = None
    cv_parsed_by: Optional[str] = None


from typing import List, Optional

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """Represents a skill possessed by a candidate"""

    id: int = Field(description="Unique identifier for the skill")
    title: str = Field(description="Name of the skill")


class Candidate(BaseModel):
    """Represents a job candidate's personal and professional information"""

    email: str = Field(description="Candidate's email address")
    first_name: str = Field(description="Candidate's first name")
    last_name: str = Field(description="Candidate's last name")
    phone: str = Field(description="Candidate's phone number")
    address: str = Field(description="Candidate's street address")
    city: str = Field(description="Candidate's city of residence")
    country: str = Field("", description="Candidate's country of residence")
    state: Optional[str] = Field(
        None, description="Candidate's state/province of residence"
    )
    skills: List[Skill] = Field(description="List of candidate's skills")
    tags: List[str] = Field(
        default=[],
        description="Additional tags associated with the candidate",
    )
    gender: str = Field(
        description="Candidate's gender. Ask the user for this if not provided."
    )
    linkedin: str = Field(
        description="Candidate's LinkedIn profile URL. Ask the user for this if not provided."
    )


class EmploymentRequirement(BaseModel):
    """Represents employment history requirement"""

    requirement: int = Field(..., description="Requirement ID")
    employer: str = Field(..., description="Employer name")
    title: str = Field(..., description="Job title")
    start: str = Field(
        ..., description="Start date of employment. Use random values of not provided"
    )
    end: str = Field(
        ..., description="End date of employment. Use random values if not provided"
    )


class EducationRequirement(BaseModel):
    """Represents education history requirement"""

    requirement: int = Field(..., description="Requirement ID")
    school: str = Field(..., description="School/University name")
    major: str = Field(..., description="Major/Degree")
    start: str = Field(
        ..., description="Start date of education. Use random values if not provided"
    )
    end: str = Field(
        ..., description="End date of education. Use random values if not provided"
    )


class NumericRequirement(BaseModel):
    """Represents numeric value requirement"""

    requirement: int = Field(..., description="Requirement ID")
    value: str = Field(..., description="Numeric value")


class URLRequirement(BaseModel):
    """Represents URL requirement"""

    requirement: int = Field(..., description="Requirement ID")
    url: str = Field(..., description="URL value")


class OptionRequirement(BaseModel):
    """Represents option selection requirement"""

    requirement: int = Field(..., description="Requirement ID")
    selected_option: int = Field(..., description="Selected option ID")


RequirementValue = Union[
    EmploymentRequirement,
    EducationRequirement,
    NumericRequirement,
    URLRequirement,
    OptionRequirement,
]


class JobApplyRequest(BaseModel):
    """Represents a job application request"""

    job: int = Field(description="ID of the job being applied to")
    candidate: Candidate = Field(description="Candidate information")
    employment_raw_txt: str = Field("", description="Raw text of employment history")
    education_raw_txt: Optional[str] = Field(
        None, description="Raw text of education history"
    )
    referred_by: Optional[str] = Field(
        None, description="ID of the person who referred the candidate"
    )
    updated_by: Optional[str] = Field(
        None, description="ID of the person who last updated the application"
    )
    stage: int = Field(
        default=1561, description="Current stage of the application process"
    )
    cv: str = Field(
        description="Path to the candidate's CV/resume file. value like 326/data/job_784/applications/49659/cv/10:32:27.783249/sample_resume.pdf"
    )
    source_type: str = Field(
        default="website", description="Type of source where the application came from"
    )
    source_value: str = Field(
        default="https://www.example.com",
        description="Must be a website",
    )
    parsed_cv: str = Field(
        description="Id of parsed CV. Get from resume. value is like parsed/724b60da65b444b698082354f6974421.json"
    )
    is_active: bool = Field(
        default=True, description="Whether the application is active"
    )
    cv_parsed_by: str = Field(
        default="arbisoft", description="Service or entity that parsed the CV"
    )
    requirement_values: List[RequirementValue] = Field(
        default=[], description="Requirement values"
    )


class ResumeParseRequest(BaseModel):
    """Represents a resume parse request"""

    resume_file_url: str = Field(
        description="The google drive URL of the user's resume file. The file should be in the user's drive and publicly shared."
    )


# ------------------------------
# API Client
# ------------------------------


class HireStreamAPIClient:
    def __init__(
        self,
        access_token: str,
        base_api_url: str = "https://cogent-labs.hirestream.io/api/v1",
        logger=None,
    ):
        self.base_api_url = base_api_url
        self.access_token = access_token
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info(
            f"Initialized HireStreamAPIClient with base URL: {base_api_url}"
        )

    async def _api_call(self, method: str, endpoint: str, payload: str = None) -> dict:
        """Utility function for API calls to the wallet.
        It sets common headers and raises errors on non-2xx responses.
        """
        url = f"{self.base_api_url}/{endpoint}"
        payload = json.dumps(payload)
        self.logger.info(f"Making {method} request to {url}")
        self.logger.debug(f"Request payload: {payload}")

        headers = {
            "Content-Type": "application/json",
            # "Authorization": f"Bearer {self.access_token}",         # Authentication not needed for hirestream
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(
                    method, url, headers=headers, data=payload, follow_redirects=False
                )

                self.logger.debug(
                    f"Response status: {response.status_code} Response: {response.text}"
                )
            if response.status_code >= 400:
                self.logger.error(f"API Error {response.status_code}: {response.text}")
                raise Exception(f"API Error {response.status_code}: {response.text}")
            try:
                return response.json()
            except Exception:
                self.logger.error(f"JSON Parsing Error: {response.text}")
                return {"text": response.text}
        except Exception as e:
            self.logger.error(f"Request failed: {str(e)}")
            traceback.print_exc()
            return {"text": str(e)}

    async def list_jobs(self) -> JobListingResponse:
        """List all jobs"""
        self.logger.info("Fetching list of all jobs")
        response = await self._api_call("GET", "jobs/published-jobs/")
        self.logger.info(f"Successfully retrieved {response.get('count', 0)} jobs")
        return response

    async def show_job_details(
        self, job_details_request: JobDetailsRequest
    ) -> JobDetailsResponse:
        """Show job details"""
        self.logger.info(
            f"Fetching details for job with UUID: {job_details_request.job_uuid}"
        )
        response = await self._api_call(
            "GET",
            f"jobs/{job_details_request.job_uuid}/view-job/?timezone=Asia%2FKarachi",
        )
        self.logger.info(
            f"Successfully retrieved details for job: {job_details_request.job_uuid}"
        )
        return response

    async def apply_to_job(self, job_apply_request: JobApplyRequest) -> Dict:
        """
        Apply to a job.

        First ask the user to upload the resume before calling this tool.
        """
        payload = job_apply_request.model_dump()
        self.logger.info(f"Applying to job: {payload}")
        response = await self._api_call(
            "POST", "workflows/job-applications/?timezone=Asia%2FKarachi", payload
        )
        self.logger.info(f"Successfully applied to job: {job_apply_request.job}")
        return response

    async def parse_resume(self, resume_parse_request: ResumeParseRequest) -> Dict:
        """
        Parse the resume file from the google drive URL

        This tool is used to parse the resume file from the google drive URL.
        It downloads the file from the google drive URL and parses it.
        It returns the parsed resume data.

        The parsed resume data is used to apply to a job.
        Only call the apply_to_job tool after calling this tool.
        """
        try:
            # Create a temporary directory for the file
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "resume.pdf")

                # Download the file from Google Drive
                self.logger.info(
                    f"Downloading resume from: {resume_parse_request.resume_file_url}"
                )
                gdown.download(
                    resume_parse_request.resume_file_url,
                    output_path,
                    quiet=False,
                    fuzzy=True,
                )

                # Upload the file to the API
                url = f"{self.base_api_url}/workflows/upload/?timezone=Asia%2FKarachi"

                async with httpx.AsyncClient(timeout=30) as client:
                    # Read file as bytes
                    with open(output_path, "rb") as file:
                        file_bytes = file.read()

                    # Send both file and type in the form data
                    files = {"file": ("resume.pdf", file_bytes, "application/pdf")}
                    data = {"type": "cv"}

                    self.logger.info("Uploading resume to API for parsing")
                    response = await client.post(url, files=files, data=data)

                    if response.status_code >= 400:
                        raise Exception(
                            f"API Error {response.status_code}: {response.text}"
                        )

                    result = response.json()
                    self.logger.info("Successfully parsed resume")
                    return result

        except Exception as e:
            self.logger.error(f"Resume parsing failed: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}


# server.py
import os
from typing import Dict


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
async def parse_resume(resume_parse_request: ResumeParseRequest) -> Dict:
    """
    Parse the resume file from the google drive URL.
    """
    try:
        return await hirestream_client.parse_resume(resume_parse_request)
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
