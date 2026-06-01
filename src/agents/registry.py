from dataclasses import dataclass
from agents.graph_agent import GraphAgent
from agents.base import BaseAgent
from schema import AgentInfo


@dataclass
class AgentEntry:
    description: str
    agent: BaseAgent


DEFAULT_AGENT = "graph_agent"


agents: dict[str, AgentEntry] = {
    "graph_agent": AgentEntry(
        description="基于 LangGraph 编排的智能体",
        agent=GraphAgent(),
    ),
}


def get_agent(agent_id: str) -> BaseAgent:
    if agent_id not in agents:
        raise KeyError(f"Agent not found: {agent_id}")
    return agents[agent_id].agent


def get_all_agent_info() -> list[AgentInfo]:
    return [
        AgentInfo(key=agent_id, description=entry.description)
        for agent_id, entry in agents.items()
    ]