from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

@CrewBase
class ContentCrew:
    """Content Writing Crew for Vector Wave"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def content_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["content_writer"],
        )

    @agent
    def content_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["content_reviewer"],
        )

    @task
    def write_content(self) -> Task:
        return Task(
            config=self.tasks_config["write_content"],
        )

    @task
    def review_content(self) -> Task:
        return Task(
            config=self.tasks_config["review_content"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Content Writing Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )