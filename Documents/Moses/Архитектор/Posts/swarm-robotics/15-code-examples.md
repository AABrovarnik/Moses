# Глава 15. Примеры кода для LLM-роёв

Практические примеры на Python для четырёх популярных фреймворков. Все примеры — минимально работающие, запускаются локально при наличии API-ключа.

> ⚠️ Зависимости: Python 3.10+, API-ключ OpenAI/Anthropic или локальная модель (Ollama).

## 0. Подготовка

```bash
# CrewAI
pip install crewai crewai-tools

# LangGraph
pip install langgraph langchain langchain-openai langchain-anthropic

# AutoGen
pip install pyautogen

# OpenAI Swarm
pip install openai-swarm
```

Переменные окружения:
```bash
export OPENAI_API_KEY="sk-..."
# или
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## 1. CrewAI — иерархия с явными ролями

### Концепция
- **Crew** = команда агентов
- **Agent** = роль + цель + backstory + инструменты
- **Task** = конкретное задание для агента
- **Process** = как агенты координируются (sequential, hierarchical, consensual)

### Пример: рой для подготовки маркетингового отчёта

```python
# crewai_example.py
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
import os

os.environ["OPENAI_API_KEY"] = "sk-..."
os.environ["SERPER_API_KEY"] = "..."

# Инструменты
search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()

# Агенты
researcher = Agent(
    role="Senior Research Analyst",
    goal="Find the latest trends in the AI agent market for 2025",
    backstory="""You are a senior research analyst with 15 years of experience
    in technology market analysis. You specialize in emerging technologies and
    can quickly identify key trends and key players.""",
    tools=[search_tool, scrape_tool],
    verbose=True,
    allow_delegation=False,
    llm="gpt-4o"
)

writer = Agent(
    role="Technical Writer",
    goal="Write a clear, structured report based on the research",
    backstory="""You are an experienced technical writer who can transform complex
    research findings into clear, actionable reports for executives.""",
    verbose=True,
    allow_delegation=False,
    llm="gpt-4o"
)

reviewer = Agent(
    role="Quality Reviewer",
    goal="Check the report for accuracy, completeness and style",
    backstory="""You are a meticulous editor with a sharp eye for detail.
    You never let inaccuracies slip through.""",
    verbose=True,
    allow_delegation=False,
    llm="gpt-4o"
)

# Задачи
research_task = Task(
    description="""Research the top 5 trends in the AI agent market for 2025.
    For each trend, identify:
    - Key players
    - Market size
    - Major use cases
    - Representative products""",
    expected_output="A structured list of 5 trends with detailed analysis",
    agent=researcher
)

write_task = Task(
    description="""Write a 5-page report based on the research findings.
    Structure it as: Executive Summary, Introduction, 5 Trends (one section each),
    Conclusion. Use clear, executive-friendly language.""",
    expected_output="A well-structured 5-page markdown report",
    agent=writer,
    context=[research_task]  # зависит от research_task
)

review_task = Task(
    description="""Review the report for:
    - Factual accuracy (cross-check with research)
    - Completeness (all 5 trends covered)
    - Style and grammar
    - Executive-readiness
    Provide specific feedback and a final score out of 10.""",
    expected_output="Review notes and a final score",
    agent=reviewer,
    context=[research_task, write_task]
)

# Команда
crew = Crew(
    agents=[researcher, writer, reviewer],
    tasks=[research_task, write_task, review_task],
    process=Process.sequential,  # или Process.hierarchical для автодиспетчера
    verbose=2,
    memory=True,  # long-term memory через vector store
    cache=True
)

# Запуск
result = crew.kickoff()
print("=== FINAL REPORT ===")
print(result)
```

### Поток выполнения
```
[Researcher] → research_task
       ↓
[Writer] → write_task (получает контекст research_task)
       ↓
[Reviewer] → review_task (получает контекст research + write)
       ↓
FINAL OUTPUT
```

### Hierarchical process
```python
crew = Crew(
    agents=[researcher, writer, reviewer],
    tasks=[research_task, write_task, review_task],
    process=Process.hierarchical,  # CrewAI назначит менеджера
    manager_llm="gpt-4o",
    verbose=2
)
```

---

## 2. LangGraph — графовая оркестрация

### Концепция
- **State** = общее состояние, которое передаётся между узлами
- **Node** = функция, которая читает/пишет в state
- **Edge** = переход между узлами (может быть условным)
- **Graph** = весь workflow

### Пример: рой с условной маршрутизацией

```python
# langgraph_example.py
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import operator
import os

os.environ["OPENAI_API_KEY"] = "sk-..."

# Состояние
class AgentState(TypedDict):
    messages: Annotated[List[str], operator.add]
    current_agent: str
    task_complete: bool
    iteration: int

llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Узлы-агенты
def researcher_node(state: AgentState) -> AgentState:
    """Исследовательский агент."""
    system = SystemMessage(content="""You are a researcher. Analyze the question
    and gather relevant information. Be concise. End your response with
    'RESEARCH_COMPLETE' when done.""")
    user = HumanMessage(content=state["messages"][-1])
    response = llm.invoke([system, user])

    return {
        "messages": [response.content],
        "current_agent": "researcher",
        "iteration": state.get("iteration", 0) + 1
    }

def analyst_node(state: AgentState) -> AgentState:
    """Аналитик — обрабатывает данные от исследователя."""
    system = SystemMessage(content="""You are an analyst. Take the research
    output and produce 3-5 key insights. End with 'ANALYSIS_COMPLETE'.""")
    user = HumanMessage(content="\n".join(state["messages"]))
    response = llm.invoke([system, user])

    return {
        "messages": [response.content],
        "current_agent": "analyst"
    }

def writer_node(state: AgentState) -> AgentState:
    """Писатель — превращает анализ в финальный отчёт."""
    system = SystemMessage(content="""You are a writer. Take the analysis and
    write a concise final report (max 200 words). End with 'WRITING_COMPLETE'.""")
    user = HumanMessage(content="\n".join(state["messages"]))
    response = llm.invoke([system, user])

    return {
        "messages": [response.content],
        "current_agent": "writer",
        "task_complete": True
    }

# Условная маршрутизация
def route_after_research(state: AgentState) -> str:
    if "RESEARCH_COMPLETE" in state["messages"][-1]:
        return "analyst"
    if state.get("iteration", 0) > 3:
        return "writer"  # fallback
    return "researcher"  # loop back

def route_after_analyst(state: AgentState) -> str:
    if "ANALYSIS_COMPLETE" in state["messages"][-1]:
        return "writer"
    return "analyst"  # loop

# Граф
workflow = StateGraph(AgentState)

workflow.add_node("researcher", researcher_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("writer", writer_node)

workflow.set_entry_point("researcher")
workflow.add_conditional_edges("researcher", route_after_research)
workflow.add_conditional_edges("analyst", route_after_analyst)
workflow.add_edge("writer", END)

app = workflow.compile()

# Запуск
result = app.invoke({
    "messages": ["What are the main differences between CrewAI and LangGraph?"],
    "current_agent": "",
    "task_complete": False,
    "iteration": 0
})

print("\n=== FINAL RESULT ===")
print(result["messages"][-1])
```

### Продвинутый паттерн: рой с параллельными агентами

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
import asyncio

class ParallelState(TypedDict):
    question: str
    researcher_output: str
    critic_output: str
    final_answer: str

def researcher(state: ParallelState) -> ParallelState:
    """Сильная сторона — факты."""
    response = llm.invoke([
        SystemMessage(content="You are a fact-focused researcher. Answer with facts only."),
        HumanMessage(content=state["question"])
    ])
    return {"researcher_output": response.content}

def critic(state: ParallelState) -> ParallelState:
    """Сильная сторона — критика."""
    response = llm.invoke([
        SystemMessage(content="You are a critical thinker. Identify weaknesses and risks."),
        HumanMessage(content=state["question"])
    ])
    return {"critic_output": response.content}

def synthesizer(state: ParallelState) -> ParallelState:
    """Объединяет результаты двух параллельных агентов."""
    response = llm.invoke([
        SystemMessage(content="You are a synthesizer. Combine fact-based and critical perspectives."),
        HumanMessage(content=f"""
        Facts: {state['researcher_output']}
        Critique: {state['critic_output']}
        Question: {state['question']}
        """)
    ])
    return {"final_answer": response.content}

# Граф с параллельным выполнением
workflow = StateGraph(ParallelState)
workflow.add_node("researcher", researcher)
workflow.add_node("critic", critic)
workflow.add_node("synthesizer", synthesizer)

# Оба стартуют параллельно
workflow.add_edge(START, "researcher")
workflow.add_edge(START, "critic")

# Оба должны завершиться, потом synthesizer
workflow.add_edge("researcher", "synthesizer")
workflow.add_edge("critic", "synthesizer")
workflow.add_edge("synthesizer", END)

app = workflow.compile()
```

### Визуализация графа

```python
from langchain_core.runnables.graph import MermaidDrawMethod

png_data = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.API
)
with open("graph.png", "wb") as f:
    f.write(png_data)
```

---

## 3. AutoGen (Microsoft) — групповой чат

### Концепция
- **ConversableAgent** — базовый класс
- **GroupChat** — все агенты в одном чате
- **GroupChatManager** — выбирает, кто говорит следующим
- Каждый агент имеет свой `system_message` и `llm_config`

### Пример: исследовательский рой

```python
# autogen_example.py
import autogen
import os

os.environ["OPENAI_API_KEY"] = "sk-..."

config = {
    "config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}],
    "cache_seed": 42,
    "temperature": 0.7
}

# Агенты
user_proxy = autogen.UserProxyAgent(
    name="User",
    human_input_mode="TERMINATE",  # спрашивает подтверждение
    max_consecutive_auto_reply=10,
    code_execution_config=False
)

planner = autogen.AssistantAgent(
    name="Planner",
    system_message="""You are a strategic planner. When given a goal,
    break it down into 3-5 concrete sub-tasks. Be specific about what
    each sub-task should produce.""",
    llm_config=config
)

researcher = autogen.AssistantAgent(
    name="Researcher",
    system_message="""You are a researcher. Execute research tasks thoroughly.
    Use web search and provide specific facts and sources.""",
    llm_config=config,
    function_map={
        "search_web": lambda q: "fake_results"
    }
)

analyst = autogen.AssistantAgent(
    name="Analyst",
    system_message="""You are an analyst. Process research data and produce
    clear insights. Distinguish facts from speculation.""",
    llm_config=config
)

critic = autogen.AssistantAgent(
    name="Critic",
    system_message="""You are a critic. Review all work for quality.
    Point out weak arguments, missing information, and bias. Be constructive.""",
    llm_config=config
)

summarizer = autogen.AssistantAgent(
    name="Summarizer",
    system_message="""You are a summarizer. When the work is complete,
    produce a clear final summary in 3 paragraphs.""",
    llm_config=config
)

# Групповой чат
groupchat = autogen.GroupChat(
    agents=[user_proxy, planner, researcher, analyst, critic, summarizer],
    messages=[],
    max_round=20,
    speaker_selection_method="auto",  # или "round_robin"
    admin_name="User"
)

manager = autogen.GroupChatManager(
    groupchat=groupchat,
    llm_config=config
)

# Запуск
user_proxy.initiate_chat(
    manager,
    message="""Research the impact of AI agents on the software development
    industry in 2024-2025. Plan the research, execute it, analyze the findings,
    and produce a final summary."""
)
```

### Speaker selection methods
- **auto** — LLM выбирает следующего (по контексту)
- **round_robin** — по очереди
- **random** — случайно
- **manual** — человек выбирает

### Кастомная функция выбора

```python
def custom_speaker_selection(last_speaker, groupchat):
    """Простая логика: planner → researcher → analyst → critic → repeat."""
    last_message = groupchat.messages[-1] if groupchat.messages else None
    if last_speaker.name == "Planner":
        return groupchat.agent_by_name("Researcher")
    elif last_speaker.name == "Researcher":
        return groupchat.agent_by_name("Analyst")
    elif last_speaker.name == "Analyst":
        return groupchat.agent_by_name("Critic")
    elif last_speaker.name == "Critic":
        return groupchat.agent_by_name("Summarizer")
    return None  # завершение

groupchat = autogen.GroupChat(
    agents=[...],
    speaker_selection_method=custom_speaker_selection
)
```

---

## 4. OpenAI Swarm — лёгкий handoff

### Концепция
- Самый минималистичный фреймворк от OpenAI (2024)
- **Agent** = инструкции + функции
- **Handoff** — передача управления другому агенту
- **Variables** — общий контекст между агентами

### Пример: рой для customer support

```python
# swarm_example.py
from swarm import Swarm, Agent
import os

os.environ["OPENAI_API_KEY"] = "sk-..."

client = Swarm()

# Функции-инструменты
def check_order_status(order_id: str) -> str:
    """Проверка статуса заказа."""
    return f"Order {order_id} is in transit, expected delivery in 2 days."

def process_refund(order_id: str) -> str:
    """Обработка возврата."""
    return f"Refund for order {order_id} has been initiated. Money will arrive in 5-7 days."

def transfer_to_refunds():
    """Передать агенту возвратов."""
    return refunds_agent

def transfer_to_sales():
    """Передать агенту продаж."""
    return sales_agent

# Агенты
triage_agent = Agent(
    name="Triage",
    instructions="""You are a customer service triage agent.
    Determine whether the customer needs:
    - Order status (use check_order_status)
    - Refund (transfer to refunds)
    - Sales inquiry (transfer to sales)
    Be brief and helpful.""",
    functions=[check_order_status, transfer_to_refunds, transfer_to_sales]
)

refunds_agent = Agent(
    name="Refunds",
    instructions="""You are a refunds specialist.
    Process refunds efficiently. Always confirm the order ID first.""",
    functions=[process_refund]
)

sales_agent = Agent(
    name="Sales",
    instructions="""You are a sales agent.
    Help customers with product information and orders.""",
    functions=[]
)

# Запуск
response = client.run(
    agent=triage_agent,
    messages=[{"role": "user", "content": "I want a refund for order 12345"}],
    debug=True
)

print(response.messages[-1]["content"])
```

### Handoff с переменными

```python
def transfer_to_technical(context_variables):
    """Передача с сохранением контекста."""
    print(f"Transferring with context: {context_variables}")
    return technical_agent

technical_agent = Agent(
    name="Technical",
    instructions="You are a technical specialist. Solve technical issues."
)
```

---

## 5. AgentVerse — роевое поведение

```bash
pip install agentverse
```

### Концепция
- **Group** = группа агентов
- **Decision** = на каждом шаге каждый агент решает, что сказать
- **Profile** = характеристики агента
- **Environment** = общее пространство

```python
# agentverse_simple.py (концепт)
from agentverse.agents.scheduler_agent import SchedulerAgent
from agentverse.agents.tool_agent import ToolAgent
from agentverse.environments import BasicEnvironment

# Агенты с разными ролями
agents = [
    ToolAgent(name="alice", role="manager",
              profile="Experienced project manager"),
    ToolAgent(name="bob", role="developer",
              profile="Senior Python developer"),
    ToolAgent(name="carol", role="designer",
              profile="UX/UI designer"),
    ToolAgent(name="dave", role="tester",
              profile="QA engineer")
]

env = BasicEnvironment(agents=agents)
# Run for N rounds
for i in range(5):
    actions = env.step()
    print(f"Round {i}: {actions}")
```

---

## 6. Сравнение фреймворков

| Критерий | CrewAI | LangGraph | AutoGen | Swarm |
|---|---|---|---|---|
| **Парадигма** | Master/worker | Граф | Групповой чат | Handoff |
| **Гибкость** | Средняя | Высокая | Высокая | Низкая |
| **Простота** | Высокая | Средняя | Средняя | Очень высокая |
| **Состояние** | Встроенное | Custom TypedDict | В чате | Variables |
| **Условная логика** | Ограниченная | Полная | Через LLM | Через handoff |
| **Параллелизм** | Нет | Да | Нет (чат) | Нет |
| **Production-ready** | Да (зрелый) | Да | Да | Нет (эксперимент) |
| **Подходит для** | Бизнес-автоматизация | Сложные workflows | Исследования | Простые рои |

## 7. Общие паттерны

### A. Паттерн «Экспертная панель»
```python
# Несколько экспертов дают мнения, арбитр выбирает
experts = [expert1, expert2, expert3, expert4]
opinions = [expert.run(issue) for expert in experts]
decision = arbiter.run(issue, opinions)
```

### B. Паттерн «Черновик → Ревью → Правки»
```python
draft = drafter.run(topic)
review = reviewer.run(draft)
final = editor.run(draft, review)
```

### C. Паттерн «Соревнование»
```python
# Несколько агентов решают одну задачу, выбираем лучший
results = [solver.run(problem) for solver in solvers]
best = max(results, key=lambda r: judge.score(r))
```

### D. Паттерн «Map-Reduce»
```python
# Агенты обрабатывают части, агрегатор собирает
parts = [worker.run(chunk) for worker in workers]
final = aggregator.run(parts)
```

### E. Паттерн «Супервайзер»
```python
# Supervisor решает, какой агент нужен следующим
while not done:
    next_agent = supervisor.choose(state, available_agents)
    result = next_agent.run(task)
    state.update(result)
```

## 8. Best practices

### Безопасность
```python
# Allow-list для инструментов
ALLOWED_TOOLS = ["search", "calculator", "file_reader"]

def safe_tool_call(tool_name, *args):
    if tool_name not in ALLOWED_TOOLS:
        raise ValueError(f"Tool {tool_name} not allowed")
    return execute_tool(tool_name, *args)
```

### Ограничение токенов
```python
# Ограничение стоимости
MAX_TOKENS_PER_AGENT = 5000
def track_tokens(agent_name, usage):
    total = state.get(f"{agent_name}_tokens", 0) + usage.total_tokens
    state[f"{agent_name}_tokens"] = total
    if total > MAX_TOKENS_PER_AGENT:
        raise TokenLimitExceeded(agent_name)
```

### Таймауты
```python
import signal

class TimeoutError(Exception):
    pass

def handler(signum, frame):
    raise TimeoutError()

signal.signal(signal.SIGALRM, handler)
signal.alarm(30)  # 30 секунд
try:
    result = agent.run(task)
finally:
    signal.alarm(0)
```

### Логирование
```python
import logging
import structlog

logger = structlog.get_logger()

def agent_step(agent_name, input, output):
    logger.info("agent_step",
                agent=agent_name,
                input_length=len(input),
                output_length=len(output))
```

### Кэширование
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_llm_call(prompt_hash, model):
    return llm.invoke(prompt_hash, model=model)
```

## 9. Отладка

### Трассировка в LangGraph
```python
config = {"recursion_limit": 25, "callbacks": [tracer]}

# Используем LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "..."
```

### Дебаг в CrewAI
```python
crew = Crew(
    agents=[...],
    tasks=[...],
    verbose=2,  # 0=silent, 1=basic, 2=detailed
    output_log_file="crew_log.txt"
)
```

### Дебаг в Swarm
```python
response = client.run(agent=..., messages=..., debug=True)
# Каждый шаг печатается в stdout
```

## 10. Полный пример: рой для code review

```python
# code_review_swarm.py
import autogen
import subprocess
import os

os.environ["OPENAI_API_KEY"] = "sk-..."

config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

# Executor — может запускать код
executor = autogen.UserProxyAgent(
    name="Executor",
    human_input_mode="NEVER",
    code_execution_config={
        "work_dir": "code_review",
        "use_docker": False  # True для безопасности
    }
)

# Архитектор — оценивает дизайн
architect = autogen.AssistantAgent(
    name="Architect",
    system_message="""You are a software architect. Review code for:
    - SOLID principles
    - Design patterns
    - Coupling and cohesion
    - Extensibility
    Be specific and cite line numbers.""",
    llm_config=config
)

# Секьюрити-аналитик — ищет уязвимости
security = autogen.AssistantAgent(
    name="Security",
    system_message="""You are a security analyst. Look for:
    - SQL injection
    - XSS, CSRF
    - Hardcoded secrets
    - Insecure dependencies
    - Authentication/authorization issues
    Use OWASP Top 10 as reference.""",
    llm_config=config
)

# Тестировщик — оценивает testability
tester = autogen.AssistantAgent(
    name="Tester",
    system_message="""You are a QA engineer. Review code for:
    - Testability
    - Edge cases
    - Error handling
    - Logging
    Suggest specific test cases.""",
    llm_config=config
)

# Lead — принимает финальное решение
lead = autogen.AssistantAgent(
    name="Lead",
    system_message="""You are the tech lead. Synthesize all reviews
    into a final verdict: APPROVE, REQUEST CHANGES, or REJECT.
    List the top 3 issues to address.""",
    llm_config=config
)

# Запуск
code_to_review = """
def get_user_data(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
"""

executor.initiate_chat(
    lead,
    message=f"Review this code:\n```python\n{code_to_review}\n```"
)
```

## 11. Метрики и мониторинг

```python
# metrics.py
import time
from dataclasses import dataclass, field
from typing import List

@dataclass
class AgentMetrics:
    name: str
    calls: int = 0
    total_tokens: int = 0
    total_time: float = 0.0
    errors: int = 0
    cache_hits: int = 0

    def avg_time(self):
        return self.total_time / self.calls if self.calls else 0

    def cost_usd(self, cost_per_1k=0.005):
        return (self.total_tokens / 1000) * cost_per_1k

# Глобальный сборщик
metrics = {}

def track(agent_name: str):
    if agent_name not in metrics:
        metrics[agent_name] = AgentMetrics(name=agent_name)
    return metrics[agent_name]

# Использование
def agent_with_metrics(agent_name, prompt):
    m = track(agent_name)
    start = time.time()
    try:
        m.calls += 1
        result = llm.invoke(prompt)
        m.total_tokens += result.usage.total_tokens
        return result.content
    except Exception as e:
        m.errors += 1
        raise
    finally:
        m.total_time += time.time() - start
```

## 12. Дальнейшие шаги

**Что попробовать:**
1. Скопировать пример CrewAI, запустить на своей задаче
2. Нарисовать workflow в LangGraph, посмотреть трассировку в LangSmith
3. Поэкспериментировать с AutoGen group chat
4. Написать собственный паттерн «Экспертная панель»

**Куда копать дальше:**
- `langchain-ai/langgraph` — примеры графов
- `microsoft/autogen` — examples/notebooks
- `crewAIInc/crewAI` — examples folder
- `openai/swarm` — examples folder
- `OpenBMB/AgentVerse` — research repo
- `geekan/MetaGPT` — software company simulation
- `camel-ai/camel` — role-playing agents

## Источники

- CrewAI docs — docs.crewai.com
- LangGraph docs — langchain-ai.github.io/langgraph
- AutoGen docs — microsoft.github.io/autogen
- OpenAI Swarm — github.com/openai/swarm
- AgentVerse — github.com/OpenBMB/AgentVerse
- LangSmith — smith.langchain.com
- OpenAI Cookbook — cookbook.openai.com
- Anthropic Claude docs — docs.anthropic.com
