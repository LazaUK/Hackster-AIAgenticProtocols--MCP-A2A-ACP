import asyncio
import os
import sys
import subprocess
import signal
import gradio as gr
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI
from agents.mcp import MCPServerStdio
from agents import (
    Agent,
    Runner,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
    gen_trace_id,
    trace
)

# MCP Server configuration
MCP_SERVER_FILE = "./MCPServer_HomeAutomation.py"

# Set up environment variables for Azure OpenAI
AOAI_API_BASE = os.getenv("AZURE_OPENAI_API_BASE")
AOAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AOAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_API_DEPLOY")

# Disable debug tracing (OPTIONAL)
set_tracing_disabled(True)

# Global variables to manage session state
agent = None
mcp_server = None
server_process = None
current_thread_id = None
previous_result = None
aoai_client = None

# Create event loop for Gradio app
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)

async def create_agent(mcp_servers=None):
    """Create or update the AI agent with optional MCP servers"""
    global agent, aoai_client
    
    # Initialise Azure OpenAI client if not already done
    if aoai_client is None:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default"
        )
        
        aoai_client = AsyncAzureOpenAI(
            api_version = AOAI_API_VERSION,
            azure_endpoint = AOAI_API_BASE,
            azure_ad_token_provider = token_provider
        )
    
    # Dynamic instructions based on MCP server availability
    if mcp_servers:
        instructions = "Use the tools to answer the questions. Maintain context from previous messages in the conversation. You now have access to home automation tools - help users control their smart home devices."
    else:
        instructions = "You are a helpful AI agent. You currently don't have access to any tools or external systems. Explain to users that they need to start the MCP server to access home automation capabilities."
    
    # Create agent with dynamic MCP servers
    agent = Agent(
        name = "Home Assistant",
        instructions = instructions,
        model = OpenAIChatCompletionsModel(
            model = AOAI_DEPLOYMENT,
            openai_client = aoai_client,
        ),
        mcp_servers = mcp_servers or [],
    )

async def initialise_llm():
    """Initialise the LLM agent without MCP server"""
    try:
        await create_agent()
        return "✅ AI Agent initialised successfully! (No MCP tools available yet)"
    except Exception as e:
        return f"❌ Error initialising LLM: {str(e)}"

async def start_mcp_server():
    """Start the MCP server process and update agent"""
    global mcp_server, server_process
    
    try:
        # Check if server file exists
        if not os.path.exists(MCP_SERVER_FILE):
            return f"❌ MCP server file not found: {MCP_SERVER_FILE}"
        
        # Start the MCP server process
        server_process = subprocess.Popen(
            [sys.executable, MCP_SERVER_FILE],
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            text = True,
            bufsize = 0
        )
        
        # Give server time to start
        await asyncio.sleep(2)
        
        if server_process.poll() is not None:
            error_output = server_process.stderr.read() if server_process.stderr else "Unknown error"
            return f"❌ Server failed to start: {error_output}"
        
        # Create MCP server connection
        mcp_server = MCPServerStdio(
            name = "Home Automation Server",
            params = {
                "command": sys.executable,
                "args": [MCP_SERVER_FILE],
            },
            cache_tools_list = True
        )
        
        # Enter the MCP server context
        await mcp_server.__aenter__()
        
        # Update agent with MCP server
        await create_agent([mcp_server])
        
        return "✅ MCP Server started! AI Agent now has access to home automation tools."
        
    except Exception as e:
        return f"❌ Error starting MCP server: {str(e)}"

async def stop_mcp_server():
    """Stop the MCP server and update agent to work without tools"""
    global mcp_server, server_process
    
    try:
        # Cleanup MCP server connection
        if mcp_server is not None:
            await mcp_server.__aexit__(None, None, None)
            mcp_server = None
        
        # Stop server process
        if server_process and server_process.poll() is None:
            if os.name == 'nt':  # Windows
                server_process.terminate()
            else:  # Unix/Linux/macOS
                server_process.send_signal(signal.SIGTERM)
            
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
        
        server_process = None
        
        # Update agent to work without MCP servers
        await create_agent()
        
        return "🛑 MCP Server stopped. AI Agent now works without tools (general assistance only)."
        
    except Exception as e:
        return f"❌ Error stopping server: {str(e)}"

async def process_user_input(user_input, history):
    """Process user input and run the agent"""
    global agent, previous_result, current_thread_id
    
    if agent is None:
        return history + [
            {"role": "user", "content": user_input, "avatar": "👤"},
            {"role": "assistant", "content": "LLM not initialised. Please restart the application.", "avatar": "🤖"}
        ], ""
    
    # If this is a new conversation
    if previous_result is None:
        current_thread_id = gen_trace_id()
    
    # Process the input
    with trace(workflow_name="Conversation", group_id=current_thread_id):
        if previous_result:
            # Add new user message to the previous conversation
            input_messages = previous_result.to_input_list() + [{"role": "user", "content": user_input}]
            result = await Runner.run(starting_agent=agent, input=input_messages)
        else:
            # First message in the conversation
            result = await Runner.run(starting_agent=agent, input=user_input)
    
    # Update previous result for next turn
    previous_result = result
    
    history.append({"role": "user", "content": user_input, "avatar": "👤"})
    history.append({"role": "assistant", "content": result.final_output, "avatar": "🤖"})
    return history, ""  # Return empty string to clear the textbox

def reset_conversation():
    """Reset conversation history"""
    global previous_result, current_thread_id
    previous_result = None
    current_thread_id = gen_trace_id()
    return [], "🔄 Conversation reset successfully!"

# Gradio wrapper functions
def gradio_initialise_llm():
    """Initialise LLM on app startup"""
    return event_loop.run_until_complete(initialise_llm())

def gradio_start_server():
    """Gradio wrapper for starting MCP server"""
    return event_loop.run_until_complete(start_mcp_server())

def gradio_stop_server():
    """Gradio wrapper for stopping MCP server"""
    return event_loop.run_until_complete(stop_mcp_server())

async def gradio_chat_async(user_input, history):
    """Async generator for streaming chat responses"""
    async for result in process_user_input_streamed(user_input, history):
        yield result

def gradio_chat(user_input, history):
    """Gradio wrapper for chat - use the global event loop"""
    return event_loop.run_until_complete(
        process_user_input(user_input, history)
    )

def shutdown():
    """Clean shutdown function"""
    if mcp_server is not None:
        event_loop.run_until_complete(mcp_server.__aexit__(None, None, None))
    event_loop.close()

def create_gradio_app():
    """Create the Gradio application"""
    
    with gr.Blocks(title="Home Automation with MCP") as app:
        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("# 🏠 Home Automation MCP Client / Server Demo")
                gr.Markdown("AI agent with dynamic tool discovery for smart home control.")
            
            with gr.Column(scale=1):
                start_btn = gr.Button("▶️ Start MCP Server", variant="primary")
                stop_btn = gr.Button("⏹️ Stop MCP Server", variant="secondary")
                status_text = gr.Textbox(
                    label="Status", 
                    value="🟡 Initializing AI Agent...",
                    interactive=False
                )
        
        # Chatbot area
        chatbot = gr.Chatbot(
            height = 300,
            type = "messages",
            show_label = False
        )
        
        with gr.Row():
            with gr.Column(scale=7):
                msg = gr.Textbox(
                    label = "Type your message here",
                    placeholder = "Ask me about your smart home devices...",
                    lines = 2,
                    show_label = False
                )
            with gr.Column(scale=1):
                submit_btn = gr.Button("Submit", variant="primary")
            with gr.Column(scale=1):
                reset_btn = gr.Button("Reset Chat", variant="secondary")
        
        # Connect app components with their functions
        start_btn.click(gradio_start_server, None, status_text)
        stop_btn.click(gradio_stop_server, None, status_text)
        
        # Use regular chat responses
        submit_btn.click(gradio_chat, [msg, chatbot], [chatbot, msg])
        msg.submit(gradio_chat, [msg, chatbot], [chatbot, msg])
        reset_btn.click(reset_conversation, None, [chatbot, status_text])
        
        # Initialize LLM on app load
        app.load(
            fn = gradio_initialise_llm,
            outputs = status_text
        )
        
    return app

def main():
    """Main function to launch the Gradio app"""
    print("🚀 Starting Home Automation MCP Client...")
    print(f"📁 MCP Server File: {MCP_SERVER_FILE}")
    print("💡 Make sure your Azure OpenAI environment variables are set!")
    print("   - AZURE_OPENAI_API_BASE")
    print("   - AZURE_OPENAI_API_VERSION") 
    print("   - AZURE_OPENAI_API_DEPLOY")
    
    try:
        app = create_gradio_app()
        app.launch(share=False)
    finally:
        shutdown()

if __name__ == "__main__":
    main()