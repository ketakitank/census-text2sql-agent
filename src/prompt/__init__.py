from src.prompt.sections import build_prompt


def get_system_prompt(
    routing_info: dict, user_query: str = "", prior_context: str = ""
) -> str:
    """
    Get the system prompt for the agent.
    Args:
        routing_info (dict): The routing information for the agent.
        user_query (str, optional): The user's query. Defaults to "".
        prior_context (str, optional): The prior context for the agent. Defaults to "".
    Returns:
        str: The system prompt for the agent.
    """
    return build_prompt(routing_info, user_query, prior_context)
