import asyncio
import os

from dotenv import load_dotenv
from browser_use import Agent, ChatGoogle

load_dotenv(dotenv_path=".env")


async def main():
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is missing from .env")

    llm = ChatGoogle(
        model="gemini-3-flash-preview",
        api_key=api_key,
    )

    agent = Agent(
        task="""
        Open https://example.com

        Inspect the page and report:
        1. Page title
        2. Main heading
        3. Available links
        4. Whether you notice any obvious functional or usability issue

        Do not modify anything.
        """,
        llm=llm,
    )

    result = await agent.run()

    print("\n========== QA RESULT ==========\n")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
