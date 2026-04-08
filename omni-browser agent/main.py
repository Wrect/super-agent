"""
CLI entrypoint for Omni Browser Agent.
Supports task execution, server mode, batch processing, and debate engine.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

from core.config import get_settings
from core.logger import setup_logger
from core.exceptions import OmniBrowserError
from agents.crew import get_omni_browser_agent
from browser.engine import close_browser_engine
from output.formatter import OutputFormatter


async def run_task(description: str, **kwargs):
    """Execute a single browser task."""
    logger = setup_logger("main", "main")
    logger.info(f"Executing task: {description}")

    try:
        agent = get_omni_browser_agent()
        result = await agent.execute_task(description, **kwargs)

        formatter = OutputFormatter()
        output = (
            formatter.format_search_results([result])
            if isinstance(result, dict) and "results" in result
            else json.dumps(result, indent=2, default=str)
        )

        print(output)
        return result

    except OmniBrowserError as e:
        logger.error(f"Task failed: {e.message}")
        print(f"Error: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await close_browser_engine()


async def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the FastAPI server."""
    logger = setup_logger("main", "main")
    logger.info(f"Starting server on {host}:{port}")

    try:
        from api.server import app
        import uvicorn

        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


async def run_batch(file_path: str):
    """Execute batch tasks from JSON file."""
    logger = setup_logger("main", "main")
    logger.info(f"Loading batch tasks from: {file_path}")

    try:
        with open(file_path, "r") as f:
            tasks = json.load(f)

        if not isinstance(tasks, list):
            raise ValueError("Batch file must contain a JSON array of tasks")

        results = []
        agent = get_omni_browser_agent()

        for i, task_data in enumerate(tasks):
            logger.info(f"Executing batch task {i + 1}/{len(tasks)}")

            description = task_data.get("description")
            if not description:
                logger.warning(f"Skipping task {i + 1}: no description")
                continue

            result = await agent.execute_task(description, **task_data)
            results.append({"task_index": i, "result": result})

        # Save results
        output_path = Path("batch_results.json")
        output_path.write_text(json.dumps(results, indent=2, default=str))
        logger.info(f"Batch complete. Results saved to {output_path}")

        print(f"Batch complete. {len(results)}/{len(tasks)} tasks executed.")

    except FileNotFoundError:
        logger.error(f"Batch file not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in batch file: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        sys.exit(1)
    finally:
        await close_browser_engine()


async def run_debate(prompt_a: str, prompt_b: str):
    """Run debate engine on two prompts."""
    logger = setup_logger("main", "main")
    logger.info("Running debate engine")

    try:
        from engine.debate import get_debate_engine

        debate_engine = get_debate_engine()
        result = await debate_engine.synthesize(prompt_a, prompt_b)

        formatter = OutputFormatter()
        output = formatter.format_synthesized_prompt(result)

        print(output)
        return result

    except Exception as e:
        logger.error(f"Debate error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Omni Browser Agent - Autonomous browser agent with social media integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Task command
    task_parser = subparsers.add_parser("task", help="Execute a browser task")
    task_parser.add_argument("description", help="Task description in natural language")
    task_parser.add_argument("--url", help="Starting URL", default=None)
    task_parser.add_argument(
        "--headless", help="Run in headless mode", action="store_true", default=True
    )
    task_parser.add_argument(
        "--headed", help="Run in headed mode", action="store_true", default=False
    )

    # Server command
    server_parser = subparsers.add_parser("server", help="Start FastAPI server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Server host")
    server_parser.add_argument("--port", type=int, default=8000, help="Server port")

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Execute batch tasks")
    batch_parser.add_argument("--file", required=True, help="Path to JSON batch file")

    # Debate command
    debate_parser = subparsers.add_parser(
        "debate", help="Run debate engine on two prompts"
    )
    debate_parser.add_argument("prompt_a", help="Historical prompt (A)")
    debate_parser.add_argument("prompt_b", help="New prompt (B)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize settings
    settings = get_settings()

    # Execute command
    if args.command == "task":
        asyncio.run(
            run_task(
                description=args.description, url=args.url, headless=not args.headed
            )
        )

    elif args.command == "server":
        asyncio.run(run_server(host=args.host, port=args.port))

    elif args.command == "batch":
        asyncio.run(run_batch(file_path=args.file))

    elif args.command == "debate":
        asyncio.run(run_debate(args.prompt_a, args.prompt_b))


if __name__ == "__main__":
    main()
