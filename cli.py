import argparse
from main import process_census_query


def main():
    parser = argparse.ArgumentParser(
        description="=== Census AI Agent: Natural Language to Snowflake SQL ==="
    )
    parser.add_argument(
        "query",
        type=str,
        nargs="?",
        help="The natural language query (e.g., 'Population of SD in 2020')",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose/debug output"
    )

    args = parser.parse_args()

    # Shared conversation history across all turns
    conversation_history = []

    if args.query:
        # Single query mode (non-interactive)
        response = process_census_query(args.query, conversation_history, args.verbose)
        _print_response(response)
    else:
        # Interactive chat mode
        print("\nCensus AI Agent (enter 'exit' to quit)\n")
        while True:
            user_q = input("You: ").strip()
            if not user_q or user_q.lower() in ("exit", "quit"):
                print("Goodbye!")
                break
            response = process_census_query(user_q, conversation_history, args.verbose)
            _print_response(response)


def _print_response(response: dict) -> None:
    if response["error"]:
        print(f"\nError: {response['error']}\n")
    elif response["answer"] != "success":
        print(f"\n  {response['answer']}\n")
    else:
        print(f"\nGenerated SQL:\n{response['sql']}\n")
        print("Results:")
        print(response["results"])
        print()


if __name__ == "__main__":
    main()
