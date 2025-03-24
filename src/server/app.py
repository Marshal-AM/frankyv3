from fastapi import FastAPI, HTTPException, BackgroundTasks

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import asyncio
import signal
import threading
from pathlib import Path
from src.cli import ZerePyCLI
import json
from fastapi.responses import StreamingResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server/app")

class ActionRequest(BaseModel):
    """Request model for agent actions"""
    connection: str
    action: str
    params: Optional[List[str]] = []

class ConfigureRequest(BaseModel):
    """Request model for configuring connections"""
    connection: str
    params: Optional[Dict[str, Any]] = {}

class ServerState:
    """Simple state management for the server"""
    def __init__(self):
        self.cli = ZerePyCLI()
        self.agent_running = False
        self.agent_task = None
        self._stop_event = threading.Event()

    def _run_agent_loop(self):
        """Run agent loop in a separate thread"""
        try:
            log_once = False
            while not self._stop_event.is_set():
                if self.cli.agent:
                    try:
                        if not log_once:
                            logger.info("Loop logic not implemented")
                            log_once = True

                    except Exception as e:
                        logger.error(f"Error in agent action: {e}")
                        if self._stop_event.wait(timeout=30):
                            break
        except Exception as e:
            logger.error(f"Error in agent loop thread: {e}")
        finally:
            self.agent_running = False
            logger.info("Agent loop stopped")

    async def start_agent_loop(self):
        """Start the agent loop in background thread"""
        if not self.cli.agent:
            raise ValueError("No agent loaded")
        
        if self.agent_running:
            raise ValueError("Agent already running")

        self.agent_running = True
        self._stop_event.clear()
        self.agent_task = threading.Thread(target=self._run_agent_loop)
        self.agent_task.start()

    async def stop_agent_loop(self):
        """Stop the agent loop"""
        if self.agent_running:
            self._stop_event.set()
            if self.agent_task:
                self.agent_task.join(timeout=5)
            self.agent_running = False

class ZerePyServer:
    def __init__(self):
        self.app = FastAPI(title="ZerePy Server")
        self.state = ServerState()
        self.setup_routes()

    def setup_routes(self):
        @self.app.get("/")
        async def root():
            """Server status endpoint"""
            return {
                "status": "running",
                "agent": self.state.cli.agent.name if self.state.cli.agent else None,
                "agent_running": self.state.agent_running
            }

        @self.app.get("/agents")
        async def list_agents():
            """List available agents"""
            try:
                agents = []
                agents_dir = Path("agents")
                if agents_dir.exists():
                    for agent_file in agents_dir.glob("*.json"):
                        if agent_file.stem != "general":
                            agents.append(agent_file.stem)
                return {"agents": agents}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/agents/{name}/load")
        async def load_agent(name: str):
            """Load a specific agent"""
            try:
                self.state.cli._load_agent_from_file(name)
                return {
                    "status": "success",
                    "agent": name
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.app.get("/connections")
        async def list_connections():
            """List all available connections"""
            if not self.state.cli.agent:
                raise HTTPException(status_code=400, detail="No agent loaded")
            
            try:
                connections = {}
                for name, conn in self.state.cli.agent.connection_manager.connections.items():
                    connections[name] = {
                        "configured": conn.is_configured(),
                        "is_llm_provider": conn.is_llm_provider
                    }
                return {"connections": connections}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/agent/action")
        async def agent_action(action_request: ActionRequest):
            """Execute a single agent action"""
            if not self.state.cli.agent:
                raise HTTPException(status_code=400, detail="No agent loaded")
            
            try:
                logger.info(f"Agent action request: {action_request.connection}, {action_request.action}, params={action_request.params}")
                
                # Special handling for chat action which expects specific format
                if action_request.action == "chat" and action_request.params:
                    logger.info(f"Processing chat request with params: {action_request.params}")
                    # If params is a list of strings, we need to use the first one as the message
                    if isinstance(action_request.params, list) and len(action_request.params) > 0:
                        if isinstance(action_request.params[0], str):
                            logger.info("Converting string parameter to chat message format")
                            action_request.params = [[{"role": "user", "content": action_request.params[0]}]]
                
                logger.info(f"Executing action with processed params: {action_request.params}")
                result = await asyncio.to_thread(
                    self.state.cli.agent.perform_action,
                    connection=action_request.connection,
                    action=action_request.action,
                    params=action_request.params
                )
                logger.info(f"Agent action result: {result}")
                return {"status": "success", "result": result}
            except Exception as e:
                logger.error(f"Error in agent action: {e}", exc_info=True)
                raise HTTPException(status_code=400, detail=str(e))

        @self.app.post("/agent/start")
        async def start_agent():
            """Start the agent loop"""
            if not self.state.cli.agent:
                raise HTTPException(status_code=400, detail="No agent loaded")
            
            try:
                await self.state.start_agent_loop()
                return {"status": "success", "message": "Agent loop started"}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.app.post("/agent/stop")
        async def stop_agent():
            """Stop the agent loop"""
            try:
                await self.state.stop_agent_loop()
                return {"status": "success", "message": "Agent loop stopped"}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.post("/connections/{name}/configure")
        async def configure_connection(name: str, config: ConfigureRequest):
            """Configure a specific connection"""
            if not self.state.cli.agent:
                raise HTTPException(status_code=400, detail="No agent loaded")
            
            try:
                connection = self.state.cli.agent.connection_manager.connections.get(name)
                if not connection:
                    raise HTTPException(status_code=404, detail=f"Connection {name} not found")
                
                success = connection.configure(**config.params)
                if success:
                    return {"status": "success", "message": f"Connection {name} configured successfully"}
                else:
                    raise HTTPException(status_code=400, detail=f"Failed to configure {name}")
                    
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/connections/{name}/status")
        async def connection_status(name: str):
            """Get configuration status of a connection"""
            if not self.state.cli.agent:
                raise HTTPException(status_code=400, detail="No agent loaded")
                
            try:
                connection = self.state.cli.agent.connection_manager.connections.get(name)
                if not connection:
                    raise HTTPException(status_code=404, detail=f"Connection {name} not found")
                    
                return {
                    "name": name,
                    "configured": connection.is_configured(verbose=True),
                    "is_llm_provider": connection.is_llm_provider
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/ollama/chat")
        async def ollama_chat(chat_request: ActionRequest):
            """Chat with Ollama using the agent's personality, with automatic tool detection and usage"""
            if not self.state.cli.agent:
                raise HTTPException(status_code=400, detail="No agent loaded")
            
            try:
                logger.info(f"Ollama chat request: {chat_request.params}")
                
                if not chat_request.params or len(chat_request.params) == 0:
                    raise HTTPException(status_code=400, detail="Message parameter is required")
                
                message = chat_request.params[0]
                logger.info(f"Processing message: {message}")
                
                # Check if this is an API tools query
                try:
                    # Import detection functions
                    from src.actions.api_tools_actions import (
                        detect_gas_price_query, detect_nft_holdings_query,
                        detect_spot_price_query, detect_token_value_query,
                        detect_token_details_query, detect_token_profitloss_query,
                        detect_transaction_trace_query, detect_transaction_history_query,
                        NETWORK_TO_CHAIN_ID
                    )
                    
                    # 1. Check for transaction trace queries
                    tx_hash, block_number, network = detect_transaction_trace_query(message)
                    if tx_hash and block_number:
                        logger.info(f"Detected transaction trace query, routing to API tools: {tx_hash}, {block_number}")
                        chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                        
                        # Call the API tools action
                        result = await asyncio.to_thread(
                            self.state.cli.agent.connection_manager.perform_action,
                            connection_name="api_tools",
                            action_name="get-transaction-trace",
                            params=[tx_hash, block_number, chain_id]
                        )
                        
                        if result:
                            logger.info("Successfully processed transaction trace query")
                            return {"status": "success", "result": result, "routed_to": "api_tools:transaction-trace"}
                    
                    # 2. Check for gas price queries
                    network = detect_gas_price_query(message)
                    if network:
                        logger.info(f"Detected gas price query, routing to API tools: {network}")
                        chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                        
                        result = await asyncio.to_thread(
                            self.state.cli.agent.connection_manager.perform_action,
                            connection_name="api_tools",
                            action_name="get-gas-price",
                            params=[chain_id]
                        )
                        
                        if result:
                            logger.info("Successfully processed gas price query")
                            return {"status": "success", "result": result, "routed_to": "api_tools:gas-price"}
                    
                    # 3. Check for NFT holdings queries
                    wallet_address, network = detect_nft_holdings_query(message)
                    if wallet_address:
                        logger.info(f"Detected NFT holdings query, routing to API tools: {wallet_address}, {network}")
                        chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                        
                        result = await asyncio.to_thread(
                            self.state.cli.agent.connection_manager.perform_action,
                            connection_name="api_tools",
                            action_name="get-nft-holdings",
                            params=[wallet_address, chain_id]
                        )
                        
                        if result:
                            logger.info("Successfully processed NFT holdings query")
                            return {"status": "success", "result": result, "routed_to": "api_tools:nft-holdings"}
                    
                    # 4. Check for token value queries
                    token_address, network = detect_token_value_query(message)
                    if token_address:
                        logger.info(f"Detected token value query, routing to API tools: {token_address}, {network}")
                        chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                        
                        result = await asyncio.to_thread(
                            self.state.cli.agent.connection_manager.perform_action,
                            connection_name="api_tools",
                            action_name="get-token-value",
                            params=[token_address, chain_id]
                        )
                        
                        if result:
                            logger.info("Successfully processed token value query")
                            return {"status": "success", "result": result, "routed_to": "api_tools:token-value"}
                    
                    # 5. Check for token details queries
                    token_address, network = detect_token_details_query(message)
                    if token_address:
                        logger.info(f"Detected token details query, routing to API tools: {token_address}, {network}")
                        chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                        
                        result = await asyncio.to_thread(
                            self.state.cli.agent.connection_manager.perform_action,
                            connection_name="api_tools",
                            action_name="get-token-details",
                            params=[token_address, chain_id]
                        )
                        
                        if result:
                            logger.info("Successfully processed token details query")
                            return {"status": "success", "result": result, "routed_to": "api_tools:token-details"}
                            
                    # 6. Check for token profit/loss queries
                    token_address, network, timerange = detect_token_profitloss_query(message)
                    if token_address:
                        logger.info(f"Detected token profit/loss query, routing to API tools: {token_address}, {network}, {timerange}")
                        chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                        
                        result = await asyncio.to_thread(
                            self.state.cli.agent.connection_manager.perform_action,
                            connection_name="api_tools",
                            action_name="get-token-profitloss",
                            params=[token_address, chain_id, timerange]
                        )
                        
                        if result:
                            logger.info("Successfully processed token profit/loss query")
                            return {"status": "success", "result": result, "routed_to": "api_tools:token-profitloss"}
                            
                    # 7. Check for spot price queries
                    currency, network = detect_spot_price_query(message)
                    if currency:
                        logger.info(f"Detected spot price query, routing to API tools: {currency}, {network}")
                        chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                        
                        result = await asyncio.to_thread(
                            self.state.cli.agent.connection_manager.perform_action,
                            connection_name="api_tools",
                            action_name="get-spot-price",
                            params=[currency, chain_id]
                        )
                        
                        if result:
                            logger.info("Successfully processed spot price query")
                            return {"status": "success", "result": result, "routed_to": "api_tools:spot-price"}
                            
                    # 8. Check for transaction history queries
                    wallet_address, network = detect_transaction_history_query(message)
                    if wallet_address:
                        logger.info(f"Detected transaction history query, routing to API tools: {wallet_address}, {network}")
                        chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                        
                        result = await asyncio.to_thread(
                            self.state.cli.agent.connection_manager.perform_action,
                            connection_name="api_tools",
                            action_name="get-transaction-history",
                            params=[wallet_address, chain_id]
                        )
                        
                        if result:
                            logger.info("Successfully processed transaction history query")
                            return {"status": "success", "result": result, "routed_to": "api_tools:transaction-history"}
                    
                except Exception as api_e:
                    logger.error(f"Error checking for API tools query: {api_e}", exc_info=True)
                    # Continue with normal Ollama processing
                
                # Not an API tools query, proceed with normal chat
                logger.info("No API tools query detected, proceeding with normal chat")
                
                # Ensure the LLM provider is set up
                if not hasattr(self.state.cli.agent, "is_llm_set") or not self.state.cli.agent.is_llm_set:
                    logger.info("Setting up LLM provider...")
                    await asyncio.to_thread(self.state.cli.agent._setup_llm_provider)
                    self.state.cli.agent.is_llm_set = True
                
                # Get the agent's system prompt
                system_prompt = self.state.cli.agent._construct_system_prompt()
                logger.info(f"Using agent system prompt: {system_prompt[:100]}...")
                
                # Use the agent to generate a response with personality
                result = await asyncio.to_thread(
                    self.state.cli.agent.prompt_llm,
                    prompt=message,
                    system_prompt=system_prompt
                )
                
                logger.info(f"Agent response: {result}")
                return {"status": "success", "result": result, "routed_to": "ollama"}
                
            except Exception as e:
                logger.error(f"Error in ollama chat: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/ollama/chat/stream")
        async def ollama_chat_stream(chat_request: ActionRequest):
            """Chat with Ollama using streaming response"""
            if not self.state.cli.agent:
                raise HTTPException(status_code=400, detail="No agent loaded")
            
            # Check if this is an API tools query before starting the stream
            if chat_request.params and len(chat_request.params) > 0:
                message = chat_request.params[0]
                try:
                    # Import detection functions
                    from src.actions.api_tools_actions import (
                        detect_gas_price_query, detect_nft_holdings_query,
                        detect_spot_price_query, detect_token_value_query,
                        detect_token_details_query, detect_token_profitloss_query,
                        detect_transaction_trace_query, detect_transaction_history_query,
                        NETWORK_TO_CHAIN_ID
                    )
                    
                    # Check for transaction trace queries
                    tx_hash, block_number, network = detect_transaction_trace_query(message)
                    if tx_hash and block_number:
                        logger.info(f"Detected transaction trace query in stream, routing to API tools: {tx_hash}, {block_number}")
                        
                        # Use a specialized streaming response for API tools
                        async def generate_api_tool_stream():
                            try:
                                yield json.dumps({
                                    "type": "log",
                                    "message": f"\n🔍 DETECTED TRANSACTION TRACE QUERY"
                                }) + "\n"
                                
                                chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                                
                                # Log the API request
                                yield json.dumps({
                                    "type": "log",
                                    "message": f"\n🔍 FETCHING TRANSACTION TRACE FOR TX {tx_hash} IN BLOCK {block_number} ON {network.upper()} (Chain ID: {chain_id})"
                                }) + "\n"
                                
                                # Call the API tools action
                                result = await asyncio.to_thread(
                                    self.state.cli.agent.connection_manager.perform_action,
                                    connection_name="api_tools",
                                    action_name="get-transaction-trace",
                                    params=[tx_hash, block_number, chain_id]
                                )
                                
                                # Return the result
                                if result:
                                    yield json.dumps({
                                        "type": "content",
                                        "message": f"\n✅ Transaction trace fetched successfully!"
                                    }) + "\n"
                                    
                                    # Format the result
                                    import json as json_lib
                                    formatted_result = json_lib.dumps(result, indent=2)
                                    
                                    # Split the result into chunks for better streaming
                                    chunk_size = 100
                                    for i in range(0, len(formatted_result), chunk_size):
                                        chunk = formatted_result[i:i+chunk_size]
                                        yield json.dumps({
                                            "type": "content",
                                            "message": chunk
                                        }) + "\n"
                                        await asyncio.sleep(0.05)
                                    
                                    yield json.dumps({
                                        "type": "end",
                                        "message": "API tools request complete"
                                    })
                                else:
                                    yield json.dumps({
                                        "type": "error",
                                        "message": "Failed to fetch transaction trace"
                                    })
                            except Exception as e:
                                logger.error(f"Error in API tools stream: {e}", exc_info=True)
                                yield json.dumps({
                                    "type": "error",
                                    "message": str(e)
                                })
                        
                        return StreamingResponse(
                            generate_api_tool_stream(),
                            media_type="application/x-ndjson"
                        )
                    
                    # Check for gas price queries
                    network = detect_gas_price_query(message)
                    if network:
                        # Similar streaming implementation for gas price
                        pass
                        
                except Exception as api_e:
                    logger.error(f"Error checking for API tools query in stream: {api_e}", exc_info=True)
                    # Continue with normal Ollama streaming
            
            # Ensure the LLM provider is set up before we start streaming
            try:
                if not hasattr(self.state.cli.agent, "is_llm_set") or not self.state.cli.agent.is_llm_set:
                    logger.info("Setting up LLM provider for streaming...")
                    await asyncio.to_thread(self.state.cli.agent._setup_llm_provider)
                    self.state.cli.agent.is_llm_set = True
            except Exception as e:
                logger.error(f"Error setting up LLM provider: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to set up LLM provider: {str(e)}")
            
            async def generate_stream():
                try:
                    if not chat_request.params or len(chat_request.params) == 0:
                        yield json.dumps({"error": "Message parameter is required"})
                        return
                    
                    message = chat_request.params[0]
                    logger.info(f"Processing streaming message: {message}")
                    
                    # Get the agent's system prompt
                    system_prompt = self.state.cli.agent._construct_system_prompt()
                    
                    # Log the start of processing
                    yield json.dumps({
                        "type": "log",
                        "message": f"\n💬 PROCESSING OLLAMA CHAT REQUEST AS {self.state.cli.agent.name}"
                    }) + "\n"
                    
                    # This is simplified as we don't have true streaming
                    # In a real implementation, we would connect to Ollama's streaming API
                    result = await asyncio.to_thread(
                        self.state.cli.agent.prompt_llm,
                        prompt=message,
                        system_prompt=system_prompt
                    )
                    
                    # Simulate streaming by yielding chunks
                    chunks = [result[i:i+10] for i in range(0, len(result), 10)]
                    for chunk in chunks:
                        yield json.dumps({
                            "type": "content",
                            "message": chunk
                        }) + "\n"
                        await asyncio.sleep(0.05)  # Small delay to simulate streaming
                    
                    # End of stream
                    yield json.dumps({
                        "type": "end",
                        "message": "Stream complete"
                    })
                    
                except Exception as e:
                    logger.error(f"Error in ollama chat stream: {e}", exc_info=True)
                    yield json.dumps({
                        "type": "error",
                        "message": str(e)
                    })
            
            return StreamingResponse(
                generate_stream(),
                media_type="application/x-ndjson"
            )

        @self.app.post("/api-tools/process")
        async def process_api_tools_request(request: ActionRequest):
            """Process a natural language request and route it to the appropriate API tool"""
            if not self.state.cli.agent:
                raise HTTPException(status_code=400, detail="No agent loaded")
            
            try:
                if not request.params or len(request.params) == 0:
                    raise HTTPException(status_code=400, detail="Message parameter is required")
                
                # Get the natural language query
                query = request.params[0]
                logger.info(f"Processing API tools query: {query}")
                
                # Import necessary functions from api_tools_actions
                from src.actions.api_tools_actions import (
                    detect_gas_price_query, detect_nft_holdings_query,
                    detect_spot_price_query, detect_token_value_query,
                    detect_token_details_query, detect_token_profitloss_query,
                    detect_transaction_trace_query, detect_transaction_history_query
                )
                
                # Check for transaction trace queries
                logger.info("Checking for transaction trace query...")
                tx_hash, block_number, network = detect_transaction_trace_query(query)
                if tx_hash and block_number:
                    logger.info(f"Detected transaction trace query with tx_hash={tx_hash}, block_number={block_number}")
                    
                    # Get chain ID from network
                    from src.actions.api_tools_actions import NETWORK_TO_CHAIN_ID
                    chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                    
                    # Call the get-transaction-trace action
                    result = await asyncio.to_thread(
                        self.state.cli.agent.perform_action,
                        connection="api_tools",
                        action="get-transaction-trace",
                        params=[tx_hash, block_number, chain_id]
                    )
                    
                    logger.info(f"Transaction trace result: {result}")
                    return {"status": "success", "result": result, "action": "get-transaction-trace"}
                
                # Check for gas price queries
                logger.info("Checking for gas price query...")
                network = detect_gas_price_query(query)
                if network:
                    logger.info(f"Detected gas price query for network: {network}")
                    
                    # Get chain ID from network
                    from src.actions.api_tools_actions import NETWORK_TO_CHAIN_ID
                    chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                    
                    # Call the get-gas-price action
                    result = await asyncio.to_thread(
                        self.state.cli.agent.perform_action,
                        connection="api_tools",
                        action="get-gas-price",
                        params=[chain_id]
                    )
                    
                    logger.info(f"Gas price result: {result}")
                    return {"status": "success", "result": result, "action": "get-gas-price"}
                
                # Check for NFT holdings queries
                logger.info("Checking for NFT holdings query...")
                wallet_address, network = detect_nft_holdings_query(query)
                if wallet_address:
                    logger.info(f"Detected NFT holdings query for wallet: {wallet_address}, network: {network}")
                    
                    # Get chain ID from network
                    from src.actions.api_tools_actions import NETWORK_TO_CHAIN_ID
                    chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                    
                    # Call the get-nft-holdings action
                    result = await asyncio.to_thread(
                        self.state.cli.agent.perform_action,
                        connection="api_tools",
                        action="get-nft-holdings",
                        params=[wallet_address, chain_id]
                    )
                    
                    logger.info(f"NFT holdings result: {result}")
                    return {"status": "success", "result": result, "action": "get-nft-holdings"}
                
                # Check for token value queries
                logger.info("Checking for token value query...")
                token_address, network = detect_token_value_query(query)
                if token_address:
                    logger.info(f"Detected token value query for token: {token_address}, network: {network}")
                    
                    # Get chain ID from network
                    from src.actions.api_tools_actions import NETWORK_TO_CHAIN_ID
                    chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                    
                    # Call the get-token-value action
                    result = await asyncio.to_thread(
                        self.state.cli.agent.perform_action,
                        connection="api_tools",
                        action="get-token-value",
                        params=[token_address, chain_id]
                    )
                    
                    logger.info(f"Token value result: {result}")
                    return {"status": "success", "result": result, "action": "get-token-value"}
                
                # Check for token details queries
                logger.info("Checking for token details query...")
                token_address, network = detect_token_details_query(query)
                if token_address:
                    logger.info(f"Detected token details query for token: {token_address}, network: {network}")
                    
                    # Get chain ID from network
                    from src.actions.api_tools_actions import NETWORK_TO_CHAIN_ID
                    chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                    
                    # Call the get-token-details action
                    result = await asyncio.to_thread(
                        self.state.cli.agent.perform_action,
                        connection="api_tools",
                        action="get-token-details",
                        params=[token_address, chain_id]
                    )
                    
                    logger.info(f"Token details result: {result}")
                    return {"status": "success", "result": result, "action": "get-token-details"}
                
                # No specific API tool query detected, fallback to Ollama
                logger.info("No specific API tool query detected, fallback to general query")
                return {"status": "error", "message": "No specific API tool query detected. Try using a more specific query format or use the Ollama chat endpoint."}
                
            except Exception as e:
                logger.error(f"Error processing API tools request: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api-tools/transaction-trace")
        async def get_transaction_trace(request: ActionRequest):
            """Direct endpoint for transaction trace requests"""
            if not self.state.cli.agent:
                raise HTTPException(status_code=400, detail="No agent loaded")
            
            try:
                logger.info(f"Transaction trace request: {request.params}")
                
                # Parameters can either be a natural language query or direct parameters
                if not request.params or len(request.params) == 0:
                    raise HTTPException(status_code=400, detail="Parameters required")
                
                tx_hash = None
                block_number = None
                network = "ethereum"
                chain_id = "1"
                
                # Check if this is a natural language query
                if len(request.params) == 1 and isinstance(request.params[0], str) and len(request.params[0]) > 50:
                    # This is likely a natural language query
                    from src.actions.api_tools_actions import detect_transaction_trace_query, NETWORK_TO_CHAIN_ID
                    query = request.params[0]
                    logger.info(f"Processing natural language transaction trace query: {query}")
                    
                    tx_hash, block_number, network = detect_transaction_trace_query(query)
                    if not tx_hash or not block_number:
                        raise HTTPException(status_code=400, detail="Could not extract transaction hash and block number from query")
                    
                    # Get chain ID from network
                    chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                    
                elif len(request.params) >= 2:
                    # Direct parameters: [tx_hash, block_number, network?]
                    tx_hash = request.params[0]
                    block_number = request.params[1]
                    
                    # Optional network parameter
                    if len(request.params) >= 3:
                        network = request.params[2]
                        from src.actions.api_tools_actions import NETWORK_TO_CHAIN_ID
                        chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                
                logger.info(f"Executing transaction trace with tx_hash={tx_hash}, block_number={block_number}, network={network}, chain_id={chain_id}")
                
                # Make sure block_number is properly formatted
                if isinstance(block_number, str) and block_number.isdigit():
                    # Convert to integer if needed by the API
                    block_number_int = int(block_number)
                    logger.info(f"Converted block_number to int: {block_number_int}")
                
                # Call the get-transaction-trace action
                # Wrap this in try/except to catch specific errors
                try:
                    logger.info(f"Calling API with params: tx_hash={tx_hash}, block_number={block_number}, chain_id={chain_id}")
                    result = await asyncio.to_thread(
                        self.state.cli.agent.connection_manager.perform_action,
                        connection_name="api_tools",
                        action_name="get-transaction-trace",
                        params=[tx_hash, block_number, chain_id]
                    )
                    
                    if not result:
                        logger.error("API returned None result")
                        raise HTTPException(status_code=500, detail="API returned empty result")
                        
                    logger.info(f"Transaction trace result type: {type(result)}")
                    logger.info(f"Transaction trace result: {str(result)[:200]}...")  # Log first 200 chars
                    return {"status": "success", "result": result}
                
                except Exception as api_error:
                    logger.error(f"API call error: {api_error}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"API call error: {str(api_error)}")
                
            except Exception as e:
                logger.error(f"Error in transaction trace: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api-tools/transaction-trace/direct")
        async def get_transaction_trace_direct(
            tx_hash: str, 
            block_number: str, 
            network: str = "ethereum"
        ):
            """Direct endpoint for transaction trace with explicit parameters"""
            if not self.state.cli.agent:
                raise HTTPException(status_code=400, detail="No agent loaded")
            
            try:
                logger.info(f"Direct transaction trace request: tx_hash={tx_hash}, block_number={block_number}, network={network}")
                
                # Get chain ID from network
                from src.actions.api_tools_actions import NETWORK_TO_CHAIN_ID
                chain_id = NETWORK_TO_CHAIN_ID.get(network.lower(), "1")
                
                # Log API call details
                logger.info(f"Making API call with params: tx_hash={tx_hash}, block_number={block_number}, chain_id={chain_id}")
                
                # Call the API directly with verbose logging
                try:
                    # First check if api_tools connection is configured
                    if not self.state.cli.agent.connection_manager.connections["api_tools"].is_configured():
                        logger.error("API Tools connection is not configured")
                        raise HTTPException(status_code=400, detail="API Tools connection is not configured")
                        
                    logger.info("API Tools connection is configured, making API call...")
                    
                    result = await asyncio.to_thread(
                        self.state.cli.agent.connection_manager.perform_action,
                        connection_name="api_tools",
                        action_name="get-transaction-trace",
                        params=[tx_hash, block_number, chain_id]
                    )
                    
                    if not result:
                        logger.error("API returned None result")
                        raise HTTPException(status_code=500, detail="API returned empty result")
                    
                    # Log successful result
                    logger.info(f"Transaction trace result received, type: {type(result)}")
                    return {"status": "success", "result": result}
                    
                except Exception as api_error:
                    logger.error(f"API call error: {api_error}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"API call error: {str(api_error)}")
                
            except Exception as e:
                logger.error(f"Error in direct transaction trace: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

def create_app():
    server = ZerePyServer()
    return server.app