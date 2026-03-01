# Census Text-to-SQL Agent (v1.0)

Introducing the **Census Text-to-SQL Agent** that translates Natural Language to Snowflake SQL using Snowflake Cortex AI to query the [US Open Census Dataset](https://urldefense.com/v3/__https://app.snowflake.com/marketplace/listing/GZSNZ2UNN0/safegraph-us-open-census-data-neighborhood-insights-free-dataset__;!!Mih3wA!AG7RCvE7t1U1XHb-7iplJr8rPXnz4G9mOp6yyv5_DD06CjntJ7XWjZpOMqTi-9A-ePe2m-ZMumwmLa3r5bxN8b4LlA8$) available for free on Snowflake marketplace.


## Key Features
1. Heuristically maps queries to the correct Census Subject Tables and specific years (2019, 2020 available in the marketplace)
2. Leverages `mistral-large2` via the `SNOWFLAKE.CORTEX.AI_COMPLETE` to ensure performant and safe sql generation
3. Post processes LLM hallucinated outputs to handle failures when output contains markdown, escaped quotes, newlines etc.
4. SQLAlchemy Data access ensures robust connection pooling and URL encoded connection handling to prevent failures 
5. Now preserves context by tracking geography, subject and query intent across follow up questions
6. Intelligently handles follow up questions that could sound off topic;
For eg: 
```
You: What is the total income for CA in 2019? 
Results:
    total_income
0  1394602475300

You: What about in 2020? # this sounds off topic since there is no mention of a state or county
Results:
   total_income_2020
0       1.462390e+12
```

## Quick Start
1. Pre-requisites 
    * Python 3.9+
    * Snowflake account with access to `US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET`

2. Installation Steps
``` 
    git clone <url>
    cd census-text2sql-agent
    pip install -r requirements.txt
```

3. Configuration Settings

    Create an `.env` file in the root directory by following [`.env.example`](./.env.example) file

4. Usage 

    Run the agent via the CLI using the `-v` flag to switch verbose to True and follow through the agent's though process.
    ```
         # Single query mode
        python cli.py "What is the population of San Diego in 2020?"

        # Verbose mode
        python cli.py "Median income in Cook County for 2019" -v

        # Interactive multi-turn mode
        python cli.py
    ```

## Project Structure
```
    .
    ├── cli.py             # CLI entry point, argument parsing & interactive loop
    ├── main.py            # Core orchestration logic & conversation history management
    ├── src/
    │   ├── agent.py       # Cortex AI inference, guardrail & SQL sanitization
    │   ├── database.py    # SQLAlchemy connection pooling & query execution
    │   ├── extractor.py   # Multi-stage geographic entity extraction
    │   ├── geography.py   # FIPS code resolution for states & counties
    │   ├── router.py      # Heuristic routing to correct Census subject tables
    │   └── prompt.py      # System prompt engineering & schema hint injection
    └── requirements.txt
```
