import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from browser_use import Agent, ChatGoogle


MODULE_DIR = Path(__file__).resolve().parent

# Anchor to the module directory: loading ".env" relatively only worked when
# the script happened to be launched from the repo root.
load_dotenv(dotenv_path=MODULE_DIR / ".env")


DEFAULT_URL = "https://example.com"

RESULTS_DIR = MODULE_DIR / "results"


async def explore(url):

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is missing. Check your .env file."
        )

    llm = ChatGoogle(
        model="gemini-3-flash-preview",
        api_key=api_key,
    )

    # The target is interpolated from `url`. It used to be hardcoded in the
    # prompt while the banner below printed a different URL, so the agent
    # silently explored a site other than the one reported.
    task = f"""
You are a professional QA website explorer.

Target website:
URL = "{url}"

Your job is to explore the website and build a structured
map of the accessible application.

IMPORTANT SAFETY RULES:

- Do NOT delete anything.
- Do NOT modify existing data.
- Do NOT submit payments.
- Do NOT send emails/messages.
- Do NOT perform destructive actions.
- Do NOT change account settings.
- Do NOT create real user records.
- Do NOT upload files.
- If an action could modify production data, skip it.

Explore the website carefully.

Identify:

1. Homepage
2. Main navigation
3. Internal pages
4. External links
5. Buttons
6. Forms
7. Input fields
8. Search functionality
9. Login/register links
10. Important application areas
11. Error pages encountered
12. Potentially interesting areas for future QA testing

For every important page, record:

- URL
- Page title
- Main heading
- Navigation links
- Buttons
- Forms
- Input fields
- Important observations

Do NOT attempt to find bugs yet.

This phase is ONLY for website discovery.

At the end, provide a structured summary of everything discovered.
"""

    print("=" * 70)
    print("AI QA AGENT - PHASE 1")
    print("Website Explorer")
    print("=" * 70)
    print(f"Target: {url}")
    print()

    agent = Agent(
        task=task,
        llm=llm,
    )

    result = await agent.run()

    result_text = str(result)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = RESULTS_DIR / f"exploration_{timestamp}.txt"

    output_file.write_text(
        result_text,
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print("EXPLORATION COMPLETE")
    print("=" * 70)
    print()
    print(result_text)
    print()
    print(f"Result saved to: {output_file}")

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Phase 1: AI-driven read-only website exploration"
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_URL,
        help=f"Target URL to explore (default: {DEFAULT_URL})",
    )
    args = parser.parse_args()

    url = args.url.strip()
    if not url.lower().startswith(("http://", "https://")):
        parser.error("url must be an absolute http(s) URL")

    try:
        asyncio.run(explore(url))
    except RuntimeError as error:
        print(f"ERROR: {error}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
