import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from browser_use import Agent, ChatGoogle


load_dotenv(dotenv_path=".env")


URL = "https://example.com"

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)


async def main():

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is missing. Check your .env file."
        )

    llm = ChatGoogle(
        model="gemini-3-flash-preview",
        api_key=api_key,
    )

    task = f"""
You are a professional QA website explorer.

Target website:
URL = "https://dplms.com"

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
    print(f"Target: {URL}")
    print()

    agent = Agent(
        task=task,
        llm=llm,
    )

    result = await agent.run()

    result_text = str(result)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

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


if __name__ == "__main__":
    asyncio.run(main())
