# Census Text-to-SQL Agent (v1.0)

Link to demo: [The AI Agent](https://census-text2sql-agent.streamlit.app/)

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
### 1. Pre-requisites 
    * Python 3.9+
    * Snowflake account with access to `US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET`

### 2. Installation Steps
``` 
    git clone <url>
    cd census-text2sql-agent
    pip install -r requirements.txt
```

### 3. Configuration Settings
Create an `.env` file in the root directory by following [`.env.example`](./.env.example) file
```
    cp .env.example .env
```

### 4. Usage 

#### CLI 
```
    # Single query mode
    python cli.py "What is the population of San Diego in 2020?"

    # Verbose/debug mode
    python cli.py "Median income in Cook County for 2019" -v

    # Interactive multi-turn mode
    python cli.py
```

#### Streamlit UI
```bash
streamlit run app.py
```

---

## Running Tests
```bash
pytest tests/
```

---

## Project Structure
```
.
├── app.py               # Streamlit web UI entry point
├── cli.py               # CLI entry point, argument parsing & interactive loop
├── main.py              # Core orchestration logic & conversation history management
├── src/
│   ├── agent.py         # Cortex AI inference, guardrail & SQL sanitization
│   ├── database.py      # SQLAlchemy connection pooling & query execution
│   ├── extractor.py     # Multi-stage geographic entity extraction
│   ├── geography.py     # FIPS code resolution for states & counties
│   ├── router.py        # Heuristic routing to correct Census subject tables
│   └── prompt.py        # System prompt engineering & schema hint injection
├── tests/
│   ├── test_router.py   # Unit tests for subject table routing
├── .env.example         # Template for environment variables
├── requirements.txt     # Pinned dependencies
└── .pre-commit-config.yaml  # Ruff linting hooks
```

## Development Process

### 1. Management of dependencies 
**Environment Parity via pinned dependencies:** I pinned all dependencies in requirements.txt via `pip freeze` to make sure the agent remains functional across deployment envs preventing any breaking changes due to upstream library updates

**Minimalist Dependency Footprint:** I removed `openai` SDK entirely after migrating to Snowflake-native inference at the start of the project, reducing external library overhead by ~20%. This resulted in faster installs and keeps third-party dependencies minimal

---

### 2. Routing Strategy 
**Keyword to Subject Code Mapping**: I have a semantic routing layer in place to map natural language key words to official subject codes (for eg: `income` => `B19`). This way we dont need to include the entire schema in the LLM window 

---

### 3. Prompt Engineering and Guardrails 

**Prompt-level SQL rules:** I used the system prompt in prompt.py to force the model to follow Snowflake's specific SQL rules. By telling the LLM exactly how to use double quotes for columns and forbidding markdown in the instructions, I made sure the code comes out ready to run

**Defensive Post-Processing:** Even though I told the LLM not to use markdown, sometimes it still wraps the SQL in triple backticks. To prevent this from breaking the database, I added a cleanup step in agent.py that strips out those extra characters. This ensures the executor always gets a clean SQL string, preventing execution failures

**Applying Guardrails**: I built in "Guardrails" to make sure the agent only answers questions about the US Census data. If a user asks about a different country or a topic that isn't in the dataset, the prompt tells the model to decline the request instead of trying to guess. This stops the agent from making up fake FIPS codes or giving wrong information

--- 

### 4. Architecture and Inference 

**Strategic Transition to Snowflake Cortex:** I moved the project from OpenAI to Snowflake’s native Cortex AI (mistral-large2). I did this for three main reasons:
- **Data Safety**: it keeps schema metadata within Snowflake
- **Performance**: it’s faster because there’s no network lag to an external API,
- **Operational Reliability:** I don't have to worry about external API limits or quotas

**Inference Engine Resilience:** During testing, I ran into some regional errors (Error 100351) where certain models weren't available in my Snowflake region. To fix this, I used mistral-large2 as my primary engine. It’s just as good at writing SQL but is much more reliable across different Snowflake regions, so the app doesn't break depending on where it’s deployed

---

### 5. Version Control and Branching Strategy

**Commits format**: I followed the  standard for all my commit messages. This makes the project history a lot easier to read by labeling changes with tags like feat: for new features, fix: for bug fixes, and docs: for documentation

**Atomic Commit Strategy**: I made sure to group the core parts of the project, like the environment setup, database connection, and the routing logic, into logical chunks. The commit history thus reflects a logical build-up 

**Feature Branch Workflow**: Once the basic setup was on the main branch, I moved all new work to separate feature branches. This keeps main stable and ready to run at all times. Riskier changes like prompt engineering were isolated in feature branches before merging

---

### 6. Developer Experience & Security
**Fail-Fast Credential Loading:** I set up the project to check for all required environment variables right when it starts. This "fail-fast" approach means that if a Snowflake password or username is missing, the app stops immediately and gives a clear error message instead of crashing later with a confusing traceback

**Onboarding via `.env.example`:** A `.env.example` template gives new contributors a clear template for required secrets, making the project easily portable and ensuring sensitive secrets are never committed to version control


## Things I would do differently if I had more time

### 1. Replace keyword mapping with embedding-based routing
This would ensure synonyms for income like wages etc. would still map to the right subject code using semantic similarity 

For example: 

![Image](./assets/TODO1.png)

I tried to retrive breakdown by counties but since I have mapped it specifically to a list mentioned [in this file](./src/prompt.py) , it only contains breakdown "by county" and not "by counties" when both are semantically same. 

### 2. ~~Schema Discovery~~
~~Currently the routing for subject code is hardcoded, if I had mroe time I would build a route map dynamically (just one time), from the live schema. This way in case new columns are added to the database the agent would stay in sync~~

### ~~3. Multi table joins~~
~~Currently the agent is unable to query multiple tables, for eg: income for various ethinicites in a particular county or state.~~

~~To fix this, the router would need to detect when a query spans multiple subject codes (e.g., `B19` for income + `B02` for race) and return all matched codes instead of just one. The system prompt would then instruct the LLM to `JOIN` those tables on their shared `GEOID` column. The main challenge is that the LLM needs to know which columns exist in each table to write a valid join, so this would also depend on having some form of schema discovery (point 2 above) in place first~~

### 4. Schema hints 

Column-level hints within each table are still hardcoded in [`prompt.py`](./src/prompt.py). If new columns are added to an existing table, the agent won't dynamically pick them up 

### **Strikethroughs Implemented** 

Router can now detect multiple subject codes per query, merges inherited tables across conversation turns, and the prompt injects multi-table JOIN instructions with aliased schema hints 
