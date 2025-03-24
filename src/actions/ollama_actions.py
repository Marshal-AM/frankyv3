import logging
from src.action_handler import register_action
from src.helpers import print_h_bar
from src.actions.api_tools_actions import detect_gas_price_query, detect_nft_holdings_query, detect_spot_price_query, detect_token_value_query, detect_token_details_query, detect_token_profitloss_query, detect_transaction_trace_query, detect_transaction_history_query, NETWORK_TO_CHAIN_ID

logger = logging.getLogger("actions.ollama_actions")

@register_action("ollama-chat")
def ollama_chat(agent, **kwargs):
    """
    Action to chat with Ollama model using the agent's personality.
    """
    logger.info(f"\n💬 STARTING OLLAMA CHAT SESSION AS {agent.name}")
    print_h_bar()
    logger.info(f"You are now chatting with {agent.name}")
    logger.info("Type 'exit' or 'quit' to end the chat session.")
    print_h_bar()
    
    # Create a system prompt from the agent's personality
    system_prompt = agent._construct_system_prompt()
    
    # Display personality info
    logger.info(f"\n🧠 Personality: {agent.name}")
    if hasattr(agent, 'traits') and agent.traits:
        logger.info(f"Traits: {', '.join(agent.traits)}")
    if hasattr(agent, 'bio') and agent.bio:
        logger.info(f"Bio: {agent.bio[0]}")
    print_h_bar()
    
    # Initialize chat with a strong personality directive
    personality_directive = f"""
You are {agent.name}. You must always stay in character and respond exactly as {agent.name} would.
Never break character or refer to yourself as 'Assistant' or any other name.
Your name is {agent.name} and you should sign your responses as {agent.name} if appropriate.

You have access to special tools that can provide real-time information. When a user asks about:
1. Gas prices or transaction fees on blockchain networks - I will fetch the current gas prices for you.
2. NFT holdings for a specific wallet address - I will fetch the NFT collection for you.
3. Spot prices of whitelisted tokens in various currencies and blockchains - I will fetch the current prices for you.
   (You can specify currencies like USD, INR, EUR and blockchains like Ethereum, Avalanche, Binance, Polygon)
4. Token value by address - I will fetch the current value of a specific token by its contract address.
   (You need to provide the token address and optionally specify the blockchain)
5. Token details by address - I will fetch detailed information about a specific token by its contract address.
   (You need to provide the token address and optionally specify the blockchain)
6. Token profit/loss by address - I will fetch profit and loss information for a specific token by its contract address.
   (You need to provide the token address and optionally specify the blockchain and time range)
7. Transaction trace - I will fetch detailed trace information for a specific transaction.
   (You need to provide the transaction hash and block number)
8. Transaction history - I will fetch the transaction history for a specific wallet address.
   (You need to provide the wallet address and optionally specify the blockchain)

Only use these tools when directly relevant to the user's query.
"""
    
    # Combine the personality directive with the system prompt
    combined_system_prompt = personality_directive + "\n\n" + system_prompt
    
    chat_history = []
    
    # Add system message to set the personality
    chat_history.append({"role": "system", "content": combined_system_prompt})
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            logger.info("\n👋 Ending chat session...")
            break
        
        # Add user message to history
        chat_history.append({"role": "user", "content": user_input})
        
        # Check if this is a gas price query
        network = detect_gas_price_query(user_input)
        
        # Check if this is an NFT holdings query
        nft_wallet_address, nft_network = detect_nft_holdings_query(user_input)
        
        # Check if this is a spot price query
        currency, spot_network = detect_spot_price_query(user_input)
        
        # Check if this is a token value query
        token_address, token_network = detect_token_value_query(user_input)
        
        # Check if this is a token details query
        details_token_address, details_token_network = detect_token_details_query(user_input)
        
        # Check if this is a token profit/loss query
        profitloss_token_address, profitloss_token_network, profitloss_timerange = detect_token_profitloss_query(user_input)
        
        # Check if this is a transaction trace query
        tx_hash, block_number, tx_network = detect_transaction_trace_query(user_input)
        
        # Check if this is a transaction history query
        wallet_address, history_network = detect_transaction_history_query(user_input)
        
        # If both token value and token details are detected, prioritize based on keywords
        if token_address and details_token_address and token_address == details_token_address:
            # Check for value-specific keywords
            value_keywords = ["value", "worth", "price", "cost", "how much"]
            value_score = sum(1 for keyword in value_keywords if keyword in user_input.lower())
            
            # Check for details-specific keywords
            details_keywords = ["details", "info", "information", "stats", "statistics", "data"]
            details_score = sum(1 for keyword in details_keywords if keyword in user_input.lower())
            
            # Log the detection scores
            logger.info(f"\n🔍 Detection scores - Value: {value_score}, Details: {details_score}")
            
            # Prioritize based on keyword scores
            if details_score > value_score:
                logger.info("\n⚠️ Both detected, but details score is higher. Prioritizing token details.")
                token_address = None
                token_network = None
            elif value_score > details_score:
                logger.info("\n⚠️ Both detected, but value score is higher. Prioritizing token value.")
                details_token_address = None
                details_token_network = None
            else:
                # If tied, default to token value as it's more commonly requested
                logger.info("\n⚠️ Both detected with equal scores. Defaulting to token value.")
                details_token_address = None
                details_token_network = None
        
        # If profit/loss query conflicts with other token queries, prioritize based on keywords
        if profitloss_token_address:
            # Check for profit/loss-specific keywords
            profitloss_keywords = ["profit", "loss", "profitloss", "roi", "return", "p&l", "gain"]
            profitloss_score = sum(1 for keyword in profitloss_keywords if keyword in user_input.lower())
            
            # If token value is also detected for the same address
            if token_address and token_address == profitloss_token_address:
                value_keywords = ["value", "worth", "price", "cost", "how much"]
                value_score = sum(1 for keyword in value_keywords if keyword in user_input.lower())
                
                logger.info(f"\n🔍 Detection scores - Value: {value_score}, Profit/Loss: {profitloss_score}")
                
                if profitloss_score > value_score:
                    logger.info("\n⚠️ Both value and profit/loss detected, but profit/loss score is higher. Prioritizing profit/loss.")
                    token_address = None
                    token_network = None
                else:
                    logger.info("\n⚠️ Both value and profit/loss detected, but value score is higher. Prioritizing value.")
                    profitloss_token_address = None
                    profitloss_token_network = None
                    profitloss_timerange = None
            
            # If token details is also detected for the same address
            if details_token_address and details_token_address == profitloss_token_address:
                details_keywords = ["details", "info", "information", "stats", "statistics", "data"]
                details_score = sum(1 for keyword in details_keywords if keyword in user_input.lower())
                
                logger.info(f"\n🔍 Detection scores - Details: {details_score}, Profit/Loss: {profitloss_score}")
                
                if profitloss_score > details_score:
                    logger.info("\n⚠️ Both details and profit/loss detected, but profit/loss score is higher. Prioritizing profit/loss.")
                    details_token_address = None
                    details_token_network = None
                else:
                    logger.info("\n⚠️ Both details and profit/loss detected, but details score is higher. Prioritizing details.")
                    profitloss_token_address = None
                    profitloss_token_network = None
                    profitloss_timerange = None
        
        # Log the detection results for debugging
        logger.info("\n🔍 QUERY DETECTION RESULTS:")
        logger.info(f"Gas price query: {network}")
        logger.info(f"NFT holdings query: {nft_wallet_address}, {nft_network}")
        logger.info(f"Spot price query: {currency}, {spot_network}")
        logger.info(f"Token value query: {token_address}, {token_network}")
        logger.info(f"Token details query: {details_token_address}, {details_token_network}")
        logger.info(f"Token profit/loss query: {profitloss_token_address}, {profitloss_token_network}, {profitloss_timerange}")
        logger.info(f"Transaction trace query: {tx_hash}, {block_number}, {tx_network}")
        logger.info(f"Transaction history query: {wallet_address}, {history_network}")
        logger.info("-" * 50)
        
        if network and "api_tools" in agent.connection_manager.connections:
            # This is a gas price query and we have the API tools connection
            try:
                # Execute the gas price action
                from src.action_handler import execute_action
                gas_result = execute_action(agent, "get-gas-price", network=network)
                
                if gas_result and not isinstance(gas_result, bool):
                    # Format the gas price information in a clearer way
                    gas_info = "EXACT CURRENT GAS PRICES (use these EXACT values in your response):\n"
                    
                    # Store the raw values for direct insertion
                    formatted_values = {}
                    
                    # Handle the nested dictionary format from 1inch API
                    if "low" in gas_result:
                        if isinstance(gas_result['low'], dict):
                            low_details = []
                            for key, value in gas_result['low'].items():
                                low_details.append(f"{key}: {value}")
                            low_value = f"{{{', '.join(low_details)}}}"
                        else:
                            low_value = str(gas_result['low'])
                        formatted_values["low"] = low_value
                        gas_info += f"- Low: {low_value} Gwei\n"
                    
                    if "standard" in gas_result:
                        if isinstance(gas_result['standard'], dict):
                            standard_details = []
                            for key, value in gas_result['standard'].items():
                                standard_details.append(f"{key}: {value}")
                            standard_value = f"{{{', '.join(standard_details)}}}"
                        else:
                            standard_value = str(gas_result['standard'])
                        formatted_values["standard"] = standard_value
                        gas_info += f"- Standard: {standard_value} Gwei\n"
                    
                    if "high" in gas_result:
                        if isinstance(gas_result['high'], dict):
                            high_details = []
                            for key, value in gas_result['high'].items():
                                high_details.append(f"{key}: {value}")
                            high_value = f"{{{', '.join(high_details)}}}"
                        else:
                            high_value = str(gas_result['high'])
                        formatted_values["high"] = high_value
                        gas_info += f"- High: {high_value} Gwei\n"
                    
                    # Create a template response
                    template_response = f"""Here are the current gas prices on {network.capitalize()}:

{gas_info}

Please provide a clear explanation of these gas prices and what they mean for users."""
                    
                    # Add a strong instruction as a system message with the template
                    chat_history.append({
                        "role": "system", 
                        "content": f"""CRITICAL INSTRUCTION: The user has asked about gas prices on {network.capitalize()}. 
I have fetched the real data above. Your response MUST include these EXACT gas price values.
DO NOT calculate, convert, or modify these values in any way.
DO NOT make up different values.
If you're unsure how to format the response, use this template:
{template_response}
"""
                    })
            except Exception as e:
                logger.error(f"\n❌ Error using gas price tool: {e}")
        
        elif nft_wallet_address and "api_tools" in agent.connection_manager.connections:
            # This is an NFT holdings query and we have the API tools connection
            try:
                # Execute the NFT holdings action
                from src.action_handler import execute_action
                nft_result = execute_action(agent, "get-nft-holdings", wallet_address=nft_wallet_address, network=nft_network)
                
                if nft_result and not isinstance(nft_result, bool):
                    # Log the raw API response
                    logger.info("\n📥 Raw API Response Data:")
                    import json
                    logger.info(json.dumps(nft_result, indent=2))
                    logger.info("\n" + "-" * 80 + "\n")
                    
                    # Format the NFT holdings information in a structured way
                    nft_info = []
                    
                    # Check if we have assets in the response
                    if "assets" in nft_result and nft_result["assets"]:
                        for asset in nft_result["assets"]:
                            # Extract basic NFT information
                            name = asset.get("name", "Unnamed NFT")
                            collection = asset.get("collection", {}).get("name", "Unknown Collection")
                            token_id = asset.get("tokenId", "Unknown ID")
                            
                            # Get token type and standard
                            token_type = asset.get("tokenType", "Unknown")
                            standard = asset.get("standard", "Unknown")
                            
                            # Format the NFT information
                            nft_entry = f"- {name} ({collection})\n"
                            nft_entry += f"  Token ID: {token_id}\n"
                            nft_entry += f"  Type: {token_type}\n"
                            nft_entry += f"  Standard: {standard}\n"
                            
                            nft_info.append(nft_entry)
                    
                    # Create a template response
                    template_response = f"""Here are the NFTs held by {nft_wallet_address} on {nft_network.capitalize()}:

{chr(10).join(nft_info) if nft_info else "No NFTs found in this wallet."}

Please provide a clear summary of the NFT holdings."""

                    # Add a strong instruction as a system message
                    chat_history.append({
                        "role": "system", 
                        "content": f"""CRITICAL INSTRUCTION: The user has asked about NFT holdings for {nft_wallet_address} on {nft_network.capitalize()}.
I have fetched the real blockchain data above. Your response MUST:
1. List all NFTs found in the wallet
2. Include collection names and token IDs
3. Mention the token types and standards
4. DO NOT make up any information not present in the data

If you're unsure how to format the response, use this template:
{template_response}
"""
                    })
            except Exception as e:
                logger.error(f"\n❌ Error using NFT holdings tool: {e}")
        
        elif currency and "api_tools" in agent.connection_manager.connections:
            # This is a spot price query and we have the API tools connection
            try:
                # Get chain ID from network name
                chain_id = NETWORK_TO_CHAIN_ID.get(spot_network.lower(), "1")  # Default to Ethereum if not found
                
                # Execute the spot price action
                from src.action_handler import execute_action
                price_result = execute_action(agent, "get-spot-price", currency=currency, chain_id=chain_id)
                
                if price_result and not isinstance(price_result, bool):
                    # Log the raw API response
                    logger.info("\n📥 Raw API Response Data:")
                    import json
                    logger.info(json.dumps(price_result, indent=2))
                    logger.info("\n" + "-" * 80 + "\n")
                    
                    # Format the price information in a structured way
                    price_info = []
                    
                    # Known token addresses and their symbols
                    token_symbols = {
                        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH",
                        "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee": "ETH",
                        "0x2c537e5624e4af88a7ae4060c022609376c8d0eb": "USDT",
                        "0xc3d688b66703497daa19211eedff47f25384cdc3": "USDC",
                        "0xd01409314acb3b245cea9500ece3f6fd4d70ea30": "LINK",
                        "0xb8c77482e45f1f44de1745f52c74426c631bdd52": "BNB",
                        "0x320623b8e4ff03373931769a31fc52a4e78b5d70": "RSR"
                    }
                    
                    # Format each token price
                    for address, price in price_result.items():
                        symbol = token_symbols.get(address, "Unknown")
                        price_info.append(f"- {symbol}: {price} {currency}")
                    
                    # Create a template response
                    template_response = f"""Here are the current spot prices for {spot_network.capitalize()} in {currency}:

{chr(10).join(price_info)}

Please provide a clear summary of the token prices."""
                    
                    # Add a strong instruction as a system message
                    chat_history.append({
                        "role": "system", 
                        "content": f"""CRITICAL INSTRUCTION: The user has asked about spot prices for {spot_network.capitalize()} in {currency}.
I have fetched the real blockchain data above. Your response MUST:
1. List all token prices in {currency}
2. Include token symbols where known
3. Format prices clearly and consistently
4. DO NOT make up any information not present in the data

If you're unsure how to format the response, use this template:
{template_response}
"""
                    })
            except Exception as e:
                logger.error(f"\n❌ Error using spot price tool: {e}")
        
        elif token_address and "api_tools" in agent.connection_manager.connections:
            # This is a token value query and we have the API tools connection
            try:
                # Get chain ID from network name
                chain_id = NETWORK_TO_CHAIN_ID.get(token_network.lower(), "1")  # Default to Ethereum if not found
                
                # Log that we're executing a token value query
                logger.info(f"\n🔍 EXECUTING TOKEN VALUE QUERY for {token_address} on {token_network} (Chain ID: {chain_id})")
                logger.info(f"API Endpoint: https://api.1inch.dev/portfolio/portfolio/v4/overview/erc20/current_value")
                
                # Execute the token value action
                from src.action_handler import execute_action
                token_result = execute_action(agent, "get-token-value", token_address=token_address, chain_id=chain_id)
                
                if token_result and not isinstance(token_result, bool):
                    # Log the raw API response
                    logger.info("\n📥 Raw API Response Data:")
                    import json
                    logger.info(json.dumps(token_result, indent=2))
                    logger.info("\n" + "-" * 80 + "\n")
                    
                    # Format the token value information in a structured way
                    token_info = []
                    total_value_usd = 0
                    
                    # Process the result to extract values
                    if "result" in token_result:
                        for protocol in token_result["result"]:
                            protocol_name = protocol.get("protocol_name", "Unknown")
                            
                            for chain_result in protocol.get("result", []):
                                if chain_result.get("chain_id") == int(chain_id):
                                    value_usd = chain_result.get("value_usd", 0)
                                    token_info.append(f"- Protocol: {protocol_name}, Value: ${value_usd:,.2f} USD")
                                    total_value_usd += value_usd
                    
                    token_info.append(f"\nTotal Value: ${total_value_usd:,.2f} USD")
                    
                    # Create a template response
                    template_response = f"""Here is the current value of token {token_address} on {token_network.capitalize()}:

{chr(10).join(token_info)}

Please provide a clear summary of the token value information."""
                    
                    # Add a strong instruction as a system message
                    chat_history.append({
                        "role": "system", 
                        "content": f"""CRITICAL INSTRUCTION: The user has asked about the value of token {token_address} on {token_network.capitalize()}.
I have fetched the real blockchain data above. Your response MUST:
1. Include the token address
2. Show the value breakdown by protocol
3. Include the total value in USD
4. DO NOT make up any information not present in the data

If you're unsure how to format the response, use this template:
{template_response}
"""
                    })
            except Exception as e:
                logger.error(f"\n❌ Error using token value tool: {e}")
        
        elif details_token_address and "api_tools" in agent.connection_manager.connections:
            # This is a token details query and we have the API tools connection
            try:
                # Get chain ID from network name
                chain_id = NETWORK_TO_CHAIN_ID.get(details_token_network.lower(), "1")  # Default to Ethereum if not found
                
                # Log that we're executing a token details query
                logger.info(f"\n🔍 EXECUTING TOKEN DETAILS QUERY for {details_token_address} on {details_token_network} (Chain ID: {chain_id})")
                logger.info(f"API Endpoint: https://api.1inch.dev/portfolio/portfolio/v4/overview/erc20/details")
                
                # Execute the token details action
                from src.action_handler import execute_action
                details_result = execute_action(agent, "get-token-details", token_address=details_token_address, chain_id=chain_id)
                
                if details_result and not isinstance(details_result, bool):
                    # Log the raw API response
                    logger.info("\n📥 Raw API Response Data:")
                    import json
                    logger.info(json.dumps(details_result, indent=2))
                    logger.info("\n" + "-" * 80 + "\n")
                    
                    # Format the token details information in a structured way
                    token_info_list = []
                    
                    # Process the result to extract token details
                    if "result" in details_result:
                        for token_info in details_result["result"]:
                            if token_info.get("chain_id") == int(chain_id):
                                # Extract basic token information
                                name = token_info.get("name", "Unknown")
                                symbol = token_info.get("symbol", "Unknown")
                                amount = token_info.get("amount", 0)
                                price_usd = token_info.get("price_to_usd", 0)
                                value_usd = token_info.get("value_usd", 0)
                                
                                # Format the token information
                                token_details = f"- Name: {name}\n"
                                token_details += f"- Symbol: {symbol}\n"
                                token_details += f"- Amount: {amount:,.6f}\n"
                                token_details += f"- Price (USD): ${price_usd:,.6f}\n"
                                token_details += f"- Value (USD): ${value_usd:,.2f}\n"
                                
                                # Add ROI if available
                                if token_info.get('roi') is not None:
                                    roi = token_info.get('roi', 0) * 100
                                    token_details += f"- ROI: {roi:.2f}%\n"
                                
                                # Add profit/loss if available
                                if token_info.get('abs_profit_usd') is not None:
                                    profit_usd = token_info.get('abs_profit_usd', 0)
                                    profit_sign = "+" if profit_usd >= 0 else ""
                                    token_details += f"- Profit/Loss: {profit_sign}${profit_usd:,.2f}\n"
                                
                                token_info_list.append(token_details)
                    
                    # Create a template response
                    template_response = f"""Here are the details for token {details_token_address} on {details_token_network.capitalize()}:

{chr(10).join(token_info_list) if token_info_list else "No token details found."}

Please provide a clear summary of the token information."""
                    
                    # Add a strong instruction as a system message
                    chat_history.append({
                        "role": "system", 
                        "content": f"""CRITICAL INSTRUCTION: The user has asked about the details of token {details_token_address} on {details_token_network.capitalize()}.
I have fetched the real blockchain data above. Your response MUST:
1. Include the token name, symbol, and address
2. Show the token amount, price, and total value
3. Include ROI and profit/loss information if available
4. DO NOT make up any information not present in the data

If you're unsure how to format the response, use this template:
{template_response}
"""
                    })
            except Exception as e:
                logger.error(f"\n❌ Error using token details tool: {e}")
        
        elif profitloss_token_address and "api_tools" in agent.connection_manager.connections:
            # This is a token profit/loss query and we have the API tools connection
            try:
                # Get chain ID from network name
                chain_id = NETWORK_TO_CHAIN_ID.get(profitloss_token_network.lower(), "1")  # Default to Ethereum if not found
                
                # Log that we're executing a token profit/loss query
                logger.info(f"\n🔍 EXECUTING TOKEN PROFIT/LOSS QUERY for {profitloss_token_address} on {profitloss_token_network} (Chain ID: {chain_id}, Timerange: {profitloss_timerange})")
                logger.info(f"API Endpoint: https://api.1inch.dev/portfolio/portfolio/v4/overview/erc20/profit_and_loss")
                
                # Execute the token profit/loss action
                from src.action_handler import execute_action
                profitloss_result = execute_action(agent, "get-token-profitloss", token_address=profitloss_token_address, chain_id=chain_id, timerange=profitloss_timerange)
                
                if profitloss_result and not isinstance(profitloss_result, bool):
                    # Log the raw API response
                    logger.info("\n📥 Raw API Response Data:")
                    import json
                    logger.info(json.dumps(profitloss_result, indent=2))
                    logger.info("\n" + "-" * 80 + "\n")
                    
                    # Format the token profit/loss information in a structured way
                    profitloss_info = []
                    
                    # Process the result to extract profit/loss data
                    if "result" in profitloss_result:
                        for pl_info in profitloss_result["result"]:
                            if pl_info.get("chain_id") == int(chain_id) or pl_info.get("chain_id") is None:
                                abs_profit_usd = pl_info.get("abs_profit_usd", 0)
                                roi = pl_info.get("roi", 0) * 100  # Convert to percentage
                                
                                profit_sign = "+" if abs_profit_usd >= 0 else ""
                                profitloss_info.append(f"- Absolute Profit/Loss: {profit_sign}${abs_profit_usd:,.2f} USD")
                                profitloss_info.append(f"- ROI: {roi:.4f}%")
                                
                                # Add timerange information
                                profitloss_info.append(f"- Time Range: {profitloss_timerange}")
                    
                    # Create a template response
                    template_response = f"""Here is the profit/loss information for token {profitloss_token_address} on {profitloss_token_network.capitalize()} over {profitloss_timerange}:

{chr(10).join(profitloss_info) if profitloss_info else "No profit/loss information found."}

Please provide a clear summary of the token's performance."""
                    
                    # Add a strong instruction as a system message
                    chat_history.append({
                        "role": "system", 
                        "content": f"""CRITICAL INSTRUCTION: The user has asked about the profit/loss of token {profitloss_token_address} on {profitloss_token_network.capitalize()} over {profitloss_timerange}.
I have fetched the real blockchain data above. Your response MUST:
1. Include the token address
2. Show the absolute profit/loss in USD
3. Include the ROI as a percentage
4. Mention the time range of the analysis
5. DO NOT make up any information not present in the data

If you're unsure how to format the response, use this template:
{template_response}
"""
                    })
            except Exception as e:
                logger.error(f"\n❌ Error using token profit/loss tool: {e}")
        
        elif tx_hash and block_number and "api_tools" in agent.connection_manager.connections:
            # This is a transaction trace query and we have the API tools connection
            try:
                # Get chain ID from network name
                chain_id = NETWORK_TO_CHAIN_ID.get(tx_network.lower(), "1")  # Default to Ethereum if not found
                
                # Log that we're executing a transaction trace query
                logger.info(f"\n🔍 EXECUTING TRANSACTION TRACE QUERY for TX {tx_hash} in block {block_number} on {tx_network} (Chain ID: {chain_id})")
                logger.info(f"API Endpoint: https://api.1inch.dev/traces/v1.0/chain/{chain_id}/block-trace/{block_number}/tx-hash/{tx_hash}")
                
                # Execute the transaction trace action
                from src.action_handler import execute_action
                trace_result = execute_action(agent, "get-transaction-trace", tx_hash=tx_hash, block_number=block_number, chain_id=chain_id)
                
                if trace_result and not isinstance(trace_result, bool):
                    # Log the raw API response
                    logger.info("\n📥 Raw API Response Data:")
                    import json
                    logger.info(json.dumps(trace_result, indent=2))
                    logger.info("\n" + "-" * 80 + "\n")
                    
                    # Format the transaction trace information in a structured way
                    trace_info = []
                    
                    # Process the result to extract transaction trace data
                    if "transactionTrace" in trace_result:
                        trace = trace_result["transactionTrace"]
                        
                        # Extract basic transaction information
                        tx_hash = trace.get("txHash", "Unknown")
                        from_addr = trace.get("from", "Unknown")
                        to_addr = trace.get("to", "Unknown")
                        value = trace.get("value", "0x0")
                        gas_limit = trace.get("gasLimit", "Unknown")
                        gas_used = trace.get("gasUsed", "Unknown")
                        gas_price = trace.get("gasPrice", "Unknown")
                        status = trace.get("status", "Unknown")
                        
                        # Format the transaction information
                        trace_info.append(f"Transaction Hash: {tx_hash}")
                        trace_info.append(f"From: {from_addr}")
                        trace_info.append(f"To: {to_addr}")
                        trace_info.append(f"Value: {value}")
                        trace_info.append(f"Gas Limit: {gas_limit}")
                        trace_info.append(f"Gas Used: {gas_used}")
                        trace_info.append(f"Gas Price: {gas_price}")
                        trace_info.append(f"Status: {status}")
                        
                        # Add logs information if available
                        if "logs" in trace and trace["logs"]:
                            trace_info.append("\nTransaction Logs:")
                            for idx, log in enumerate(trace["logs"], 1):
                                trace_info.append(f"\nLog #{idx}:")
                                trace_info.append(f"Contract: {log.get('contract', 'Unknown')}")
                                trace_info.append(f"Data: {log.get('data', 'None')}")
                                if "topics" in log and log["topics"]:
                                    trace_info.append("Topics:")
                                    for topic_idx, topic in enumerate(log["topics"], 1):
                                        trace_info.append(f"  {topic_idx}. {topic}")
                        
                        # Add calls information if available
                        if "calls" in trace and trace["calls"]:
                            trace_info.append("\nInternal Calls:")
                            for idx, call in enumerate(trace["calls"], 1):
                                trace_info.append(f"\nCall #{idx}:")
                                trace_info.append(f"Type: {call.get('type', 'Unknown')}")
                                trace_info.append(f"From: {call.get('from', 'Unknown')}")
                                trace_info.append(f"To: {call.get('to', 'Unknown')}")
                                trace_info.append(f"Value: {call.get('value', '0x0')}")
                    
                    # Create a template response
                    template_response = f"""Here is the transaction trace for TX {tx_hash} in block {block_number} on {tx_network.capitalize()}:

{chr(10).join(trace_info)}

Please provide a clear explanation of this transaction trace, including what the transaction did and any notable events or internal calls."""
                    
                    # Add a strong instruction as a system message
                    chat_history.append({
                        "role": "system", 
                        "content": f"""CRITICAL INSTRUCTION: The user has asked about the transaction trace for TX {tx_hash} in block {block_number} on {tx_network.capitalize()}.
I have fetched the real blockchain data above. Your response MUST:
1. Include the transaction hash, from/to addresses, and value
2. Explain the transaction status and gas usage
3. Describe any logs or events emitted during the transaction
4. Explain any internal calls made during the transaction
5. DO NOT make up any information not present in the data

If you're unsure how to format the response, use this template:
{template_response}
"""
                    })
            except Exception as e:
                logger.error(f"\n❌ Error using transaction trace tool: {e}")
        
        elif wallet_address and "api_tools" in agent.connection_manager.connections:
            # This is a transaction history query and we have the API tools connection
            try:
                # Get chain ID from network name
                chain_id = NETWORK_TO_CHAIN_ID.get(history_network.lower(), "1")  # Default to Ethereum if not found
                
                # Log that we're executing a transaction history query
                logger.info(f"\n🔍 EXECUTING TRANSACTION HISTORY QUERY for wallet {wallet_address} on {history_network} (Chain ID: {chain_id})")
                logger.info(f"API Endpoint: https://api.1inch.dev/history/v2.0/history/{wallet_address}/events")
                
                # Execute the transaction history action
                from src.action_handler import execute_action
                history_result = execute_action(agent, "get-transaction-history", wallet_address=wallet_address, chain_id=chain_id)
                
                if history_result and not isinstance(history_result, bool):
                    # Log the raw API response
                    logger.info("\n📥 Raw API Response Data:")
                    import json
                    logger.info(json.dumps(history_result, indent=2))
                    logger.info("\n" + "-" * 80 + "\n")
                    
                    # Format the transaction history information in a structured way
                    history_info = []
                    
                    # Process the result to extract transaction history data
                    if "items" in history_result and history_result["items"]:
                        history_info.append(f"Found {len(history_result['items'])} transactions for {wallet_address} on {history_network.capitalize()}:")
                        
                        for idx, tx in enumerate(history_result["items"][:10], 1):  # Limit to 10 transactions for readability
                            if "details" in tx:
                                details = tx["details"]
                                tx_hash = details.get("txHash", "Unknown")
                                tx_type = details.get("type", "Unknown")
                                status = details.get("status", "Unknown")
                                block_number = details.get("blockNumber", "Unknown")
                                from_addr = details.get("fromAddress", "Unknown")
                                to_addr = details.get("toAddress", "Unknown")
                                
                                history_info.append(f"\nTransaction #{idx}:")
                                history_info.append(f"Hash: {tx_hash}")
                                history_info.append(f"Type: {tx_type}")
                                history_info.append(f"Status: {status}")
                                history_info.append(f"Block: {block_number}")
                                history_info.append(f"From: {from_addr}")
                                history_info.append(f"To: {to_addr}")
                                
                                # Add token actions if available
                                if "tokenActions" in details and details["tokenActions"]:
                                    history_info.append("Token Actions:")
                                    for token_action in details["tokenActions"]:
                                        token_addr = token_action.get("address", "Unknown")
                                        token_std = token_action.get("standard", "Unknown")
                                        token_amount = token_action.get("amount", "0")
                                        token_direction = token_action.get("direction", "Unknown")
                                        
                                        history_info.append(f"  Token: {token_addr}")
                                        history_info.append(f"  Standard: {token_std}")
                                        history_info.append(f"  Amount: {token_amount}")
                                        history_info.append(f"  Direction: {token_direction}")
                        
                        if len(history_result["items"]) > 10:
                            history_info.append(f"\n... and {len(history_result['items']) - 10} more transactions (showing only the 10 most recent)")
                    else:
                        history_info.append(f"No transactions found for wallet {wallet_address} on {history_network.capitalize()}.")
                    
                    # Create a template response
                    template_response = f"""Here is the transaction history for wallet {wallet_address} on {history_network.capitalize()}:

{chr(10).join(history_info)}

Please provide a clear summary of this wallet's transaction activity."""
                    
                    # Add a strong instruction as a system message
                    chat_history.append({
                        "role": "system", 
                        "content": f"""CRITICAL INSTRUCTION: The user has asked about the transaction history for wallet {wallet_address} on {history_network.capitalize()}.
I have fetched the real blockchain data above. Your response MUST:
1. Include the wallet address
2. Summarize the types of transactions (sends, approvals, etc.)
3. Mention any notable token transfers or interactions
4. Provide an overview of the wallet's activity pattern
5. DO NOT make up any information not present in the data

If you're unsure how to format the response, use this template:
{template_response}
"""
                    })
            except Exception as e:
                logger.error(f"\n❌ Error using transaction history tool: {e}")
        
        # Get response from Ollama
        try:
            response = agent.connection_manager.perform_action(
                connection_name="ollama",
                action_name="chat",
                params=[chat_history]
            )
            
            if response:
                # Check if this was a gas price query and if the response contains the gas data
                if network and "api_tools" in agent.connection_manager.connections:
                    # Check if the response contains gas price data
                    contains_gas_data = False
                    
                    # Look for key indicators that the model used the gas data
                    if network.lower() in response.lower():
                        contains_gas_data = True
                    
                    # Check for gas-related keywords
                    gas_keywords = ["gas", "gwei", "fee", "price"]
                    if any(keyword in response.lower() for keyword in gas_keywords):
                        contains_gas_data = True
                    
                    # If the model didn't use the gas data, append a correction
                    if not contains_gas_data and 'template_response' in locals():
                        logger.info("\n⚠️ Model didn't use gas data. Adding correction...")
                        
                        # Create a corrected response that includes the agent's style but with the correct data
                        corrected_response = f"{response}\n\nActually, let me provide you with the exact gas prices:\n\n{template_response}"
                        
                        # Update the response
                        response = corrected_response
                
                # Check if this was an NFT holdings query and if the response contains the NFT data
                elif nft_wallet_address and "api_tools" in agent.connection_manager.connections:
                    # Check if the response contains NFT data
                    contains_nft_data = False
                    
                    # Look for key indicators that the model used the NFT data
                    if nft_wallet_address in response:
                        contains_nft_data = True
                    
                    if "assets" in nft_result and nft_result["assets"]:
                        contains_nft_data = True
                    
                    # If the model didn't use the NFT data, append a correction
                    if not contains_nft_data and 'template_response' in locals():
                        logger.info("\n⚠️ Model didn't use NFT data. Adding correction...")
                        
                        # Create a corrected response that includes the agent's style but with the correct data
                        corrected_response = f"{response}\n\nActually, let me provide you with the exact NFT data:\n\n{template_response}"
                    
                    # Update the response
                    response = corrected_response
            
                # Check if this was a spot price query and if the response contains the price data
                elif currency and "api_tools" in agent.connection_manager.connections:
                    # Check if the response contains price data
                    contains_price_data = False
                    
                    # Look for key indicators that the model used the price data
                    if currency in response:
                        contains_price_data = True
                    
                    # Check for price-related keywords
                    price_keywords = ["price", "spot", "token", "value"]
                    if any(keyword in response.lower() for keyword in price_keywords):
                        contains_price_data = True
                    
                    # If the model didn't use the price data, append a correction
                    if not contains_price_data and 'template_response' in locals():
                        logger.info("\n⚠️ Model didn't use price data. Adding correction...")
                        
                        # Create a corrected response that includes the agent's style but with the correct data
                        response = f"{response}\n\nActually, let me provide you with the exact spot prices:\n\n{template_response}"
                
                # Check if this was a token value query and if the response contains the token data
                elif token_address and "api_tools" in agent.connection_manager.connections:
                    # Check if the response contains token value data
                    contains_token_data = False
                    
                    # Look for key indicators that the model used the token data
                    if token_address in response:
                        contains_token_data = True
                    
                    # Check for token-related keywords
                    token_keywords = ["token", "value", "worth", "usd", "protocol"]
                    if any(keyword in response.lower() for keyword in token_keywords):
                        contains_token_data = True
                    
                    # If the model didn't use the token data, append a correction
                    if not contains_token_data and 'template_response' in locals():
                        logger.info("\n⚠️ Model didn't use token value data. Adding correction...")
                        
                        # Create a corrected response that includes the agent's style but with the correct data
                        response = f"{response}\n\nActually, let me provide you with the exact token value information:\n\n{template_response}"
                
                # Check if this was a token details query and if the response contains the token details
                elif details_token_address and "api_tools" in agent.connection_manager.connections:
                    # Check if the response contains token details data
                    contains_details_data = False
                    
                    # Look for key indicators that the model used the token details
                    if details_token_address in response:
                        contains_details_data = True
                    
                    # Check for token details-related keywords
                    details_keywords = ["token", "details", "name", "symbol", "price", "value", "amount"]
                    if any(keyword in response.lower() for keyword in details_keywords):
                        contains_details_data = True
                    
                    # If the model didn't use the token details, append a correction
                    if not contains_details_data and 'template_response' in locals():
                        logger.info("\n⚠️ Model didn't use token details data. Adding correction...")
                        
                        # Create a corrected response that includes the agent's style but with the correct data
                        response = f"{response}\n\nActually, let me provide you with the exact token details information:\n\n{template_response}"
                
                # Check if this was a token profit/loss query and if the response contains the profit/loss data
                elif profitloss_token_address and "api_tools" in agent.connection_manager.connections:
                    # Check if the response contains profit/loss data
                    contains_profitloss_data = False
                    
                    # Look for key indicators that the model used the profit/loss data
                    if profitloss_token_address in response:
                        contains_profitloss_data = True
                    
                    # Check for profit/loss-related keywords
                    profitloss_keywords = ["profit", "loss", "roi", "return", "performance", "usd"]
                    if any(keyword in response.lower() for keyword in profitloss_keywords):
                        contains_profitloss_data = True
                    
                    # If the model didn't use the profit/loss data, append a correction
                    if not contains_profitloss_data and 'template_response' in locals():
                        logger.info("\n⚠️ Model didn't use token profit/loss data. Adding correction...")
                        
                        # Create a corrected response that includes the agent's style but with the correct data
                        response = f"{response}\n\nActually, let me provide you with the exact token profit/loss information:\n\n{template_response}"
                
                # Check if this was a transaction trace query and if the response contains the trace data
                elif tx_hash and block_number and "api_tools" in agent.connection_manager.connections:
                    # Check if the response contains transaction trace data
                    contains_trace_data = False
                    
                    # Look for key indicators that the model used the trace data
                    if tx_hash in response:
                        contains_trace_data = True
                    
                    # Check for trace-related keywords
                    trace_keywords = ["transaction", "trace", "tx", "hash", "block", "from", "to", "gas", "logs", "calls"]
                    if any(keyword in response.lower() for keyword in trace_keywords):
                        contains_trace_data = True
                    
                    # If the model didn't use the trace data, append a correction
                    if not contains_trace_data and 'template_response' in locals():
                        logger.info("\n⚠️ Model didn't use transaction trace data. Adding correction...")
                        
                        # Create a corrected response that includes the agent's style but with the correct data
                        response = f"{response}\n\nActually, let me provide you with the exact transaction trace information:\n\n{template_response}"
                
                # Check if this was a transaction history query and if the response contains the history data
                elif wallet_address and "api_tools" in agent.connection_manager.connections:
                    # Check if the response contains transaction history data
                    contains_history_data = False
                    
                    # Look for key indicators that the model used the history data
                    if wallet_address in response:
                        contains_history_data = True
                    
                    # Check for history-related keywords
                    history_keywords = ["transaction", "history", "wallet", "sent", "received", "transfer", "approve"]
                    if any(keyword in response.lower() for keyword in history_keywords):
                        contains_history_data = True
                    
                    # If the model didn't use the history data, append a correction
                    if not contains_history_data and 'template_response' in locals():
                        logger.info("\n⚠️ Model didn't use transaction history data. Adding correction...")
                        
                        # Create a corrected response that includes the agent's style but with the correct data
                        response = f"{response}\n\nActually, let me provide you with the exact transaction history information:\n\n{template_response}"
            
                # Print the response
                logger.info(f"\n{agent.name}: {response}")
                
                # Add assistant response to history
                chat_history.append({"role": "assistant", "content": response})
            else:
                logger.error("\n❌ Failed to get response from Ollama")
        except Exception as e:
            logger.error(f"\n❌ Error in Ollama chat: {e}")
    
    return True 