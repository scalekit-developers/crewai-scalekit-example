"""
CrewAI multi-agent email triage with Scalekit-authenticated Gmail tools.

Run: python agent.py

Three agents collaborate to triage a Gmail inbox:
  1. Inbox Scanner — fetches unread emails
  2. Prioritizer   — classifies emails by urgency
  3. Draft Writer  — generates reply drafts for high-priority items

Gmail access is handled by Scalekit AgentKit via MCP.
"""

import os
from typing import Any, Optional

import scalekit.client
from crewai import Agent, Crew, LLM, Process, Task
from crewai_tools import MCPServerAdapter
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# ---------------------------------------------------------------------------
# CrewAI schema patch — Scalekit tool schemas include nullable fields
# (e.g. {"type": ["string", "null"]}), which CrewAI's built-in JSON Schema
# converter does not handle. This patch adds support for nullable types.
# ---------------------------------------------------------------------------
import crewai.utilities.pydantic_schema_utils as _schema_mod

_orig = _schema_mod._json_schema_to_pydantic_type


def _patched(json_schema: dict[str, Any], root_schema: dict[str, Any], **kwargs: Any) -> Any:
    type_ = json_schema.get("type")
    if isinstance(type_, list):
        non_null = [t for t in type_ if t != "null"]
        has_null = "null" in type_
        inner = _orig(
            {**json_schema, "type": non_null[0] if non_null else "string"},
            root_schema,
            **kwargs,
        )
        return Optional[inner] if has_null else inner
    return _orig(json_schema, root_schema, **kwargs)


_schema_mod._json_schema_to_pydantic_type = _patched

# ---------------------------------------------------------------------------
# Scalekit client
# ---------------------------------------------------------------------------

scalekit_client = scalekit.client.ScalekitClient(
    client_id=os.getenv("SCALEKIT_CLIENT_ID"),
    client_secret=os.getenv("SCALEKIT_CLIENT_SECRET"),
    env_url=os.getenv("SCALEKIT_ENV_URL"),
)
actions = scalekit_client.actions

USER_ID = os.getenv("SCALEKIT_USER_IDENTIFIER", "user_123")

# ---------------------------------------------------------------------------
# Ensure Gmail connection is authorized
# ---------------------------------------------------------------------------

response = actions.get_or_create_connected_account(
    connection_name="gmail",
    identifier=USER_ID,
)
if response.connected_account.status != "ACTIVE":
    link = actions.get_authorization_link(
        connection_name="gmail",
        identifier=USER_ID,
    )
    print("\n[gmail] Authorization required.")
    print(f"Open this link:\n\n  {link.link}\n")
    input("Press Enter after authorizing...")

# ---------------------------------------------------------------------------
# Get MCP URL for Gmail tools
# ---------------------------------------------------------------------------

mcp_config_name = os.getenv("SCALEKIT_MCP_CONFIG_NAME", "gmail-user-tools")

inst_response = actions.mcp.ensure_instance(
    config_name=mcp_config_name,
    user_identifier=USER_ID,
)
mcp_url = inst_response.instance.url
print(f"[ok] MCP instance ready: {mcp_url}")

# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------

llm = LLM(
    model=os.getenv("LLM_MODEL", "gpt-4o"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
)

# ---------------------------------------------------------------------------
# Agents and tasks
# ---------------------------------------------------------------------------

with MCPServerAdapter({"url": mcp_url, "transport": "streamable-http"}) as tools:
    scanner = Agent(
        role="Inbox Scanner",
        goal="Fetch the user's latest unread emails and extract key metadata.",
        backstory=(
            "You are an efficient assistant that reads a Gmail inbox and "
            "returns a structured summary of unread messages including "
            "subject, sender, date, and a one-line preview."
        ),
        tools=tools,
        llm=llm,
        verbose=True,
    )

    prioritizer = Agent(
        role="Email Prioritizer",
        goal="Classify each email by urgency: high, medium, or low.",
        backstory=(
            "You are an expert at triaging incoming messages. You consider "
            "sender importance, subject keywords, and time sensitivity to "
            "assign a priority level to each email."
        ),
        llm=llm,
        verbose=True,
    )

    drafter = Agent(
        role="Reply Drafter",
        goal="Draft short, professional replies for high-priority emails.",
        backstory=(
            "You are a concise writer who drafts polite, on-point email "
            "replies. You focus only on high-priority items and keep each "
            "draft under 100 words."
        ),
        llm=llm,
        verbose=True,
    )

    scan_task = Task(
        description=(
            "Fetch the last 5 unread emails from Gmail. For each email, "
            "return: subject, sender name, sender email, date, and a "
            "one-sentence preview of the body."
        ),
        expected_output=(
            "A numbered list of 5 emails with subject, sender, date, "
            "and preview for each."
        ),
        agent=scanner,
    )

    prioritize_task = Task(
        description=(
            "Take the list of emails from the Inbox Scanner and classify "
            "each one as high, medium, or low priority. Consider sender "
            "importance, urgency cues in the subject, and whether the email "
            "requires a response."
        ),
        expected_output=(
            "The same list of emails, each now tagged with a priority "
            "level (high / medium / low) and a brief reason."
        ),
        agent=prioritizer,
    )

    draft_task = Task(
        description=(
            "For each email marked as high priority by the Prioritizer, "
            "draft a short, professional reply (under 100 words). Skip "
            "medium and low priority emails."
        ),
        expected_output=(
            "A list of draft replies, one per high-priority email, "
            "including the original subject line and the draft text."
        ),
        agent=drafter,
    )

    crew = Crew(
        agents=[scanner, prioritizer, drafter],
        tasks=[scan_task, prioritize_task, draft_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    print("\n" + "=" * 60)
    print("CREW RESULT")
    print("=" * 60)
    print(result)
