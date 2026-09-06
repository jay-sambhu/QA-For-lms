"""
Phase 18 E2E Real Browser Benchmark Execution Script.
Starts local Uvicorn benchmark app on http://127.0.0.1:8099 and runs JASUSS autonomously against it.
"""
import asyncio
import json
import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import uvicorn
from multiprocessing import Process

from run_qa import run_pipeline
from tests.fixtures.demo_app.main import app as demo_app


def start_server():
    uvicorn.run(demo_app, host="127.0.0.1", port=8099, log_level="warning")


async def run_benchmark():
    print("Starting background Uvicorn server on http://127.0.0.1:8099...")
    proc = Process(target=start_server, daemon=True)
    proc.start()
    time.sleep(2)  # Wait for server startup

    target_url = "http://127.0.0.1:8099"
    run_id = f"e2e_benchmark_{int(time.time())}"
    output_dir = os.path.join(os.getcwd(), "results", "e2e_benchmark")

    print(f"Executing JASUSS Autonomous Pipeline against real browser target: {target_url}")
    result = await run_pipeline(
        target_url,
        max_pages=15,
        run_id=run_id,
        output_dir=output_dir,
    )

    proc.terminate()
    if not result:
        print("ERROR: E2E Benchmark Pipeline failed!")
        return 1

    print("\n" + "=" * 70)
    print("E2E BENCHMARK EXECUTION COMPLETED SUCCESSFULLY!")
    print(f"Report JSON: {result['json_path']}")
    print(f"Report Markdown: {result['md_path']}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run_benchmark()))
