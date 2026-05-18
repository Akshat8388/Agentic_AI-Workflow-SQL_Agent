from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
from langchain_experimental.tools import PythonREPLTool
from langgraph.graph import StateGraph, START, END, add_messages
#from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
#from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate,ChatPromptTemplate,MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import TypedDict,Annotated,List,Optional,Literal
from langchain_core.messages import BaseMessage,HumanMessage,AIMessage
from langchain_ollama import ChatOllama
#from langchain_openai import ChatOpenAI
#from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_community.tools import TavilySearchResults
from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')
import os
import uuid

load_dotenv()
#********************** HuggingFACE Endpoint *****************************
#huggingFace_llm = HuggingFaceEndpoint(repo_id="openai/gpt-oss-20b",temperature=0,streaming=True)
#model = ChatHuggingFace(llm=huggingFace_llm)

#***************************** GEMINI API KEY ***************************
#google_model = ChatGoogleGenerativeAI(model ="gemini-2.5-flash",temperature=0,streaming=True)

#**************************** GROQ API KEY *******************************
#google_model = ChatGroq(model = "openai/gpt-oss-120b",streaming=True, temperature=0)

#************************** Kaggle Ollama API KEY *******************************
#TUNNEL_URL = "https://saturninely-shiftier-lyda.ngrok-free.dev/"
google_model = ChatOllama(
    model="gemma4:31b-cloud",
    base_url="https://ollama.com",
    client_kwargs={"headers": {"Authorization": "Bearer " + os.environ.get("OLLAMA_API_KEY")}},
    temperature=0
)
#**************************** Github API KEY *****************************
#google_model = ChatOpenAI(model="openai/gpt-4.1",api_key=github_token,base_url="https://models.github.ai/inference",temperature=0)

#***************************** NVIDIA API KEY *******************************
#google_model = ChatNVIDIA(model = "google/gemma-4-31b-it",temperature=0)

BASE_DIR = os.getenv("PLOTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots"))

python_tool = PythonREPLTool()
search_tool = TavilySearchResults(max_results=3)

class AgentState(TypedDict):
    messages : Annotated[List[BaseMessage],add_messages]
    query_checker : Literal["need_sql_agent","no_need_of_sql_agent_and_visualize_agent","need_visualize_agent"]
    db_connection : bool
    db_path : Optional[str]
    query_safety_checker : Literal["safe", "dangerous"]
    warning_msg : Optional[str]
    status : Optional[Literal["yes","no"]]
    img_path : Optional[str]
    agent_answer : Optional[str]
    user_id: Optional[int]  

class Query_Checker(BaseModel):
    query_checker : Literal["need_sql_agent","no_need_of_sql_agent_and_visualize_agent","need_visualize_agent"] = Field(description="Determines whether the user's query requires the SQL agent or visualize agent or not needed both of them.")
    
class Query_Analysis(BaseModel):
    query_analysis: Literal["safe", "dangerous"] = Field(
        description="Classify the user's query as it 'safe' or 'dangerous'(delete, update, drop, or other destructive operations) for database operations."
    )
 
class VisualizationDecision(BaseModel):
    decision: Literal["yes", "no"] = Field(description="classify the user's message into 'yes' or 'no' whether the user want data visualization or not.")    
    
parser = PydanticOutputParser(pydantic_object=Query_Checker)  

query_analysis_parser = PydanticOutputParser(pydantic_object=Query_Analysis)  

visual_parser = PydanticOutputParser(pydantic_object=VisualizationDecision)

def user_query_checker(state: AgentState):
    messages = state.get("messages", [])
    # ✅ Only look at last 6 messages for routing decision
    trimmer = MessagesPlaceholder("history", n_messages=6)
    trimmed = trimmer.format_messages(history=messages)
    
    conversation_history = "\n".join([
        f"{msg.type}: {msg.content}" for msg in trimmed
    ])

    template = PromptTemplate(
        template="""
        You are the router of an intelligent SQL Agent application.

        **Your job:**
        Analyze the full conversation and understand the user's **intent** — not just their words.
        Use your intelligence to decide which route fits best:

        - "need_sql_agent": The user's intent is related to the database in any way.
          This includes exploring, querying, modifying, or understanding the connected database.
         
        - "need_visualize_agent": The user explicitly wants a chart, graph, plot, or
          any kind of visual representation of data from a previous query result.

        - "no_need_of_sql_agent_and_visualize_agent": The user is asking something
          completely unrelated to the database — general knowledge, casual conversation,
          or anything that has no database intent whatsoever.

        {format_instructions}

        **Conversation History:**
        {conversation}
        """,
        input_variables=["conversation"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    prompt = template.format(
        conversation=conversation_history
    )

    output = google_model.invoke(prompt)
    content = getattr(output, "content", output)

    try:
        parsed = parser.parse(content)
        return {"query_checker": parsed.query_checker}
    except Exception:
        return {"query_checker": "no_need_of_sql_agent_and_visualize_agent"}

def general_LLM_agent(state: AgentState):
    system_prompt ="""You are a part of SQL Agent application. You are not a generic chatbot. You are a specialized AI assistant that works with other agents in this application.

Your application has 4 agents that work together:
- A **Router** that reads every user message and decides who should handle it
- A **SQL Agent** that connects to databases, writes and executes SQL queries, and fetches results  
- A **Visualization Agent** that takes SQL results and generates charts and graphs 
- You — the **General Agent** — who handles everything else

Your application has special feature for asking human approval if user action is to modify or update the database.
You have access to a web search tool. Use it when the user asks about current events, recent news, or anything that needs up-to-date information.

Your answer should be concise and aware of your place in the application."""
    
    agent = create_react_agent(model=google_model, tools=[search_tool], prompt=system_prompt)
    result = agent.invoke({"messages": state["messages"]})

    return {"messages": [result["messages"][-1]]}


def database_connection_checker(state: AgentState):
    db_path = state.get("db_path")
    
    if not db_path or db_path == None or db_path == "":
        return {
            "db_connection": False,
            "messages": [AIMessage(content="❌ No database connected. Please connect a database first and try again.")]
        }
    
    try:
        db = SQLDatabase.from_uri(db_path)
        db.run("SELECT 1")
        return {"db_connection": True}
    except Exception as e:
        return {
            "db_connection": False,
            "messages": [AIMessage(content=f"❌ Database connection failed: {str(e)}")]
        }
    
    
def query_analysis(state : AgentState):
    messages = getattr(state["messages"][-1], "content", str(state["messages"][-1]))
    
    template = PromptTemplate(
        template="""
        Classify the following user query as either 'safe' or 'dangerous' for database operations.
        Safe: Queries that are safe for performing sql operations on database.
        Dangerous: Queries that can modify or delete data (DELETE, UPDATE, DROP, INSERT, etc.).

        {format_instructions}

        user query: {conversation}
        """,
        input_variables=["conversation"],
        partial_variables={"format_instructions": query_analysis_parser.get_format_instructions()}
    )

   
    prompt = template.format(conversation=messages)
    
    
    output = google_model.invoke(prompt)
    content = getattr(output, "content", str(output))
    
    try:
        parsed = query_analysis_parser.parse(content)
        return {"query_safety_checker": parsed.query_analysis}
    except Exception as e:
        return {"query_safety_checker": "safe"}

def human_node(state: AgentState):
    query = getattr(state["messages"][-1], "content", str(state["messages"][-1]))

    template = PromptTemplate(
        template="""
        The user has requested a database write operation that requires confirmation before proceeding.

        User request: "{query}"

        Generate a short, polite confirmation message asking the user if they would like to proceed (Yes/No).
        Keep it professional and concise.
        """,
        input_variables=["query"]
    )

    prompt = template.format(query=query)
    output = google_model.invoke(prompt)
                     
    return {
        "warning_msg": AIMessage(content=output.content),
    }

def sql_agent(state : AgentState):
    db_path = state.get("db_path")
    db = SQLDatabase.from_uri(db_path)

    toolkit = SQLDatabaseToolkit(db=db, llm=google_model)
    tools = toolkit.get_tools()
    
    system_prompt = """
    You are an agent designed to interact with a SQL database.
    You have been given access to a set of tools to query and retrieve information from the database.

    **Your primary instruction is to start by listing the tables in the database to understand the schema. Do not skip this step.**

    Here are the tools available to you:
    - **sql_db_list_tables**: Use this tool to get the names of all tables in the database.
    - **sql_db_schema**: Use this tool to get the schema (column names and types) for specific tables.
    - **sql_db_query**: Use this tool to execute a SQL query against the database.
    - **sql_db_query_checker**: Use this tool to check a SQL query for syntax errors before executing it.

    Given an input question, follow these steps:
    1.  Use **sql_db_list_tables** to see what tables are available.
    2.  Use **sql_db_schema** to understand the structure of the relevant tables if neccessary.
    3.  Construct a syntactically correct SQL query for the '{dialect}' dialect.
    4.  Use **sql_db_query_checker** to validate your query.
    5.  Execute the query using **sql_db_query**.
    6.  Look at the results and provide answer to the user.
    7.  Only ask "Would you like to visualize this data?" if ALL of these are true:
        - The result contains **multiple rows** of numeric or categorical data
        - The data is suitable for a chart (e.g. counts, averages, totals grouped by category)
        - Examples that qualify: salary by department, employee count per city, sales over time
        - Examples that DO NOT qualify: a single value, a yes/no answer, a list of names, a single row result, text-only results

    **STRICT RULES:**
        - You are **approved** to run destructive queries like DELETE rows, UPDATE, INSERT.
        - You are **STRICTLY FORBIDDEN** from executing DROP DATABASE, or any query that destroys the entire database. If the user asks for this, refuse and explain you cannot do that.
    Unless the user specifies a number of examples, limit your SELECT queries to at most {top_k} results.
    """
   
    sys_prompt = system_prompt.format(dialect=db.dialect, top_k=5)

    sql_agent = create_react_agent(google_model, tools=tools, prompt=sys_prompt)

    trimmer = MessagesPlaceholder("history", n_messages=10)
    trimmed_messages = trimmer.format_messages(history=state["messages"])
   
    input_query = {"messages": trimmed_messages}

    result = sql_agent.invoke(input_query)

    return {"messages":[result["messages"][-1]],"agent_answer":result["messages"][-1]}
    
def visualization_agent(state: AgentState):
    user_id = state.get("user_id")
    plots_dir = os.path.join(BASE_DIR, str(user_id))
    os.makedirs(plots_dir, exist_ok=True)
    unique_filename = f"plot_{uuid.uuid4()}.png"
    file_path = os.path.join(plots_dir, unique_filename)
    img_path = f"/plots/{user_id}/{unique_filename}"

    sql_answer = state.get("agent_answer")
    data_summary = sql_answer.content if sql_answer else "No data available."

    task = f"""
    You are an expert Python data visualization assistant.The visualization agent of SQLAgent — a multi-agent SQL application.
    Your task is to visualize the data described in the following Data Summary.

    Other agents in your system:
    - **The Router** decides which agent handles each user request.
    - **SQL Agent** runs database queries and produces data results.
    - **General Agent** handles general conversation and questions.

    ###Your job:
    - If **Data Summary** is available: Write Python code, create a highly aesthetic, professional beautiful chart (BAR, PIE, LINE, etc).
    - If **data Summary** says "No data available": Do NOT generate any chart or run any code Because your **Co-agent - SQL AGENT** hasn't run any query yet so you don't have data to visualize. So, respond conversationally by using your intelligence -> SQL_AGENT hasn't provided the data yet. Once a query has been run and a data summary is provided, I’ll be happy to create a chart for you!.**

    **Data Summary from SQL Agent:** "{data_summary}"

    **Instructions for Generating a chart:**
    1. Write Python code to put this data into a pandas DataFrame.
    2. Use Matplotlib to generate a suitable **beautiful** plot like (BAR chart,PIE chart,LINE chart,etc...) from the DataFrame.
    3. **STYLING REQUIREMENTS for creating beautiful charts:**
       - Use a professional color palette (not the default blue).
       - Add a clear Title, X-axis label, and Y-axis label with appropriate font sizes.
       - Ensure x-axis labels do not overlap (rotate them by 45 degrees if there are many categories).
       - You MUST include `plt.tight_layout()` at the end of your plotting code so labels are not cut off.
    4. Save the final plot to a file named '{file_path}'.
    5. Execute the code using your available tool.
    6. After saving the plot , Describe ONLY -> **The data Summary insight** in natural language like **Here is the ... chart that shows ... You can see that ...**.
    """

    agent = create_react_agent(model=google_model, tools=[python_tool])
    result = agent.invoke({"messages": [HumanMessage(content=task)]})

    final_answer_message = result["messages"][-1]

    # ✅ Embed img_path inside AIMessage content as a special tag
    # so it gets persisted in SQLite with the messages
    combined_content = f"{final_answer_message.content}\n\n[IMG]{img_path}[/IMG]"
    persisted_message = AIMessage(content=combined_content)

    return {
        "img_path": img_path,
        "messages": [persisted_message]
    }
    
def route_from_query_checker(state : AgentState):
    if state['query_checker']=="need_sql_agent":
        return "need_SQL_Agent"
    elif state["query_checker"]=="need_visualize_agent":
        return "need_visualize_Agent"
    else:
        return "not_needed"
    
def route_from_database_connection_checker(state : AgentState):
    if state["db_connection"]==True:
        return "database_connected"
    else:
        return "database_not_connected" 
    
def route_from_query_safety_analysis(state : AgentState):
    if state["query_safety_checker"] == "dangerous":
        return "dangerous"
    else:
        return "safe"
    
def route_from_human_node(state : AgentState):
    if state.get("status")=="yes":
        return "continue"
    else:
        return "cancel"
       
graph = StateGraph(AgentState)

graph.add_node("checking_user_query",user_query_checker)
graph.add_node("checking_database_connection",database_connection_checker)
graph.add_node("query_safety_analysis",query_analysis)
graph.add_node("human_approval",human_node)
graph.add_node("SQL_Agent",sql_agent)
graph.add_node("visualization_agent",visualization_agent)
graph.add_node("general_LLM_agent",general_LLM_agent)

graph.add_edge(START,"checking_user_query")
graph.add_conditional_edges("checking_user_query",route_from_query_checker,{"need_SQL_Agent":"checking_database_connection","need_visualize_Agent":"visualization_agent","not_needed":"general_LLM_agent"})
graph.add_conditional_edges("checking_database_connection",route_from_database_connection_checker,{"database_connected":"query_safety_analysis","database_not_connected":END})
graph.add_conditional_edges("query_safety_analysis",route_from_query_safety_analysis,{"dangerous":"human_approval","safe":"SQL_Agent"})
graph.add_conditional_edges("human_approval",route_from_human_node,{"continue":"SQL_Agent","cancel":END})
graph.add_edge("SQL_Agent",END)
graph.add_edge("visualization_agent",END)
graph.add_edge("general_LLM_agent",END)      
