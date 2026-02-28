import argparse
from main import process_census_query

def main():
    parser = argparse.ArgumentParser(
        description="=== Census AI Agent: Natural Language to Snowflake SQL ==="
    )
    parser.add_argument(
        "query", 
        type=str, 
        nargs='?', 
        help="The natural language query (e.g., 'Population of SD in 2020')"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose/debug output"
    )
    
    args = parser.parse_args()

    # Default query if none provided
    user_q = args.query if args.query else "What is the total population of San Diego in 2020?"
    
    process_census_query(user_q, args.verbose)

if __name__ == "__main__":
    main()
