# Hackster Learning Series: AI Agentic Protocols

This GitHub repo complements The Learning Series articles on [Hackster.io](https://www.hackster.io/) about **AI Agentic Protocols**. It covers:
- the **Model Context Protocol (MCP)** for dynamic tool and data access,
- the **Agent2Agent Protocol (A2A)** for direct agent collaboration,
- and the **Agent Communication Protocol (ACP)** for robust, interoperable communication.

The repo includes Python code to jump-start practical implementation of these protocols, offering immediate application opportunities.

## 📑 Table of contents:
- [Environment Setup]()
- [Part 1: Model Context Protocol (MCP)]()
- [Part 2: Agent2Agent Protocol (A2A)]()
- [Part 3: Agent Communication Protocol (ACP)]()
- [Demo videos on YouTube]()

## Environment Setup
1. Install the required Python packages, listed in the provided *requirements.txt*:
``` PowerShell
pip install -r requirements.txt
```
2. If using Azure OpenAI as your AI backend, set the following environment variables:

| Variable                | Description                                      |
| ----------------------- | ------------------------------------------------ |
| `AOAI_API_BASE`         | Base URL of the Azure OpenAI endpoint            |
| `AOAI_API_VERSION`      | API version of the Azure OpenAI endpoint         |
| `AOAI_DEPLOYMENT`       | Deployment name of the Azure OpenAI model        |

## Part 1: Model Context Protocol (MCP)
This section demonstrates how an AI agent can dynamically discover and use external tools. The implementation uses an **MCP Server** (`MCPServer_HomeAutomation.py`) to expose home automation functionalities (tools) and an **MCP Client** (`MCPClient_GradioUI.py`) as a Gradio UI for user interaction.

1.  **Defining MCP Tools and Resources (MCP Server):** functions decorated with `@mcp.tool()` or `@mcp.resource()` in the `MCPServer_HomeAutomation.py` file define callable actions (Tools) or retrievable data (Resources) for the AI.

    ``` Python
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("Home Automation")

    @mcp.tool()
    def control_light(action: str) -> str: # Generalized snippet
        # ...
        return "Light controlled."

    @mcp.resource("home://device_status")
    def get_device_status() -> str: # Generalized snippet
        # ...
        return "{}"

    if __name__ == "__main__":
        mcp.run() # Starts the MCP server
    ```

2.  **Establishing MCP Server Connection (MCP Client):** the `MCPClient_GradioUI.py` starts the server as a subprocess and connects using `MCPServerStdio` to enable tool discovery.

    ``` Python
    import subprocess
    from agents.mcp import MCPServerStdio
    
    server_process = subprocess.Popen([...]) # Start server

    mcp_server = MCPServerStdio(...)
    await mcp_server.__aenter__() # Initialize connection
    ```

4.  **Initialising AI Agent with MCP Servers (MCP Client):**
    An `Agent` is initialised with the connected `mcp_servers`. The agent's instructions are dynamically updated based on MCP tool availability.

    ``` Python
    from agents import Agent, OpenAIChatCompletionsModel
    
    agent = Agent(
        name="Home Assistant",
        instructions="Use tools...",
        model=OpenAIChatCompletionsModel(...),
        mcp_servers=[mcp_server], # Link MCP server
    )
    ```

5.  **Processing User Input and Running Agent (MCP Client):** when a user inputs a query, `Runner.run()` is invoked. The AI model, aware of the MCP tools, decides whether to call a relevant tool or access a resource via the MCP layer to fulfill the request.

    ```Python
    from agents import Runner
    
    async def process_user_input(user_input, agent):
        result = await Runner.run(starting_agent=agent, input=user_input)
        return result.final_output
    ```

> [!NOTE]
> Hackster article about MCP can be accessed [here](PROVIDE_URL).

## Part 2: Agent2Agent Protocol (A2A)

> [!Caution]
> Work in progress. To be updated soon!

## Part 3: Agent Communication Protocol (ACP)

> [!Caution]
> Work in progress. To be updated soon!

## Demo videos on YouTube
