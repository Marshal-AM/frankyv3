import logging
import re
from src.action_handler import register_action
from src.helpers import print_h_bar

logger = logging.getLogger("actions.api_tools_actions")

# Dictionary mapping network names to chain IDs
NETWORK_TO_CHAIN_ID = {
    "ethereum": "1",
    "eth": "1",
    "mainnet": "1",
    "binance": "56",
    "bsc": "56",
    "polygon": "137",
    "matic": "137",
    "avalanche": "43114",
    "avax": "43114",
    "arbitrum": "42161",
    "optimism": "10",
    "base": "8453",
    "fantom": "250",
    "ftm": "250",
    "aurora":"1313161554"
}

@register_action("get-gas-price")
def get_gas_price(agent, **kwargs):
    """
    Action to get gas price for a specific blockchain network.
    This will be triggered when the user asks about gas prices.
    """
    # Check if chain_id is provided in kwargs
    chain_id = kwargs.get("chain_id")
    network = kwargs.get("network")
    
    # If network name is provided, convert to chain_id
    if network and not chain_id:
        network = network.lower()
        chain_id = NETWORK_TO_CHAIN_ID.get(network)
        if not chain_id:
            logger.error(f"\n❌ Unknown network: {network}")
            return False
    
    # If no chain_id or network provided, default to Ethereum
    if not chain_id:
        chain_id = "1"  # Default to Ethereum
        network = "Ethereum"
    else:
        # Find network name from chain ID for display
        for net, cid in NETWORK_TO_CHAIN_ID.items():
            if cid == chain_id:
                network = net.capitalize()
                break
        else:
            network = f"Chain ID {chain_id}"
    
    logger.info(f"\n🔍 FETCHING GAS PRICE FOR {network.upper()} (Chain ID: {chain_id})")
    print_h_bar()
    
    # Call the API through the connection
    result = agent.connection_manager.perform_action(
        connection_name="api_tools",
        action_name="get-gas-price",
        params=[chain_id]
    )
    
    if result and "error" not in result:
        logger.info(f"\n✅ Current gas prices for {network}:")
        
        # Format and display the gas price information
        if "low" in result:
            logger.info(f"Low: {result['low']} Gwei")
        if "standard" in result:
            logger.info(f"Standard: {result['standard']} Gwei")
        if "fast" in result:
            logger.info(f"Fast: {result['fast']} Gwei")
        if "instant" in result:
            logger.info(f"Instant: {result['instant']} Gwei")
        if "baseFee" in result:
            logger.info(f"Base Fee: {result['baseFee']} Gwei")
            
        return result
    else:
        error = result.get("error", "Unknown error") if result else "Failed to get gas price"
        logger.error(f"\n❌ {error}")
        return False

def detect_gas_price_query(text):
    """
    Detect if a user query is asking about gas prices.
    Returns the network name if found, otherwise None.
    """
    # Patterns to match gas price queries
    gas_patterns = [
        r"(?:what(?:'s| is) the|current|check|get|show) (?:gas|gas price|gas fee)",
        r"gas (?:price|fee|cost)",
        r"how much (?:gas|fee)",
        r"transaction fee",
        r"network fee"
    ]
    
    # Check if any gas pattern matches
    is_gas_query = any(re.search(pattern, text.lower()) for pattern in gas_patterns)
    
    if not is_gas_query:
        return None
    
    # If it's a gas query, try to extract the network
    for network in NETWORK_TO_CHAIN_ID.keys():
        if network.lower() in text.lower():
            return network
    
    # Default to Ethereum if no specific network mentioned
    return "ethereum"

@register_action("get-nft-holdings")
def get_nft_holdings(agent, **kwargs):
    """
    Action to get NFT holdings for a specific wallet address on a blockchain.
    This will be triggered when the user asks about NFTs owned by a wallet.
    """
    # Check if wallet_address and chain_id are provided in kwargs
    wallet_address = kwargs.get("wallet_address")
    chain_id = kwargs.get("chain_id")
    network = kwargs.get("network")
    
    # If network name is provided, convert to chain_id
    if network and not chain_id:
        network = network.lower()
        chain_id = NETWORK_TO_CHAIN_ID.get(network)
        if not chain_id:
            logger.error(f"\n❌ Unknown network: {network}")
            return False
    
    # If no chain_id or network provided, default to Ethereum
    if not chain_id:
        chain_id = "1"  # Default to Ethereum
        network = "Ethereum"
    else:
        # Find network name from chain ID for display
        for net, cid in NETWORK_TO_CHAIN_ID.items():
            if cid == chain_id:
                network = net.capitalize()
                break
        else:
            network = f"Chain ID {chain_id}"
    
    if not wallet_address:
        logger.error("\n❌ No wallet address provided")
        return False
    
    logger.info(f"\n🔍 FETCHING NFT HOLDINGS FOR {wallet_address} ON {network.upper()} (Chain ID: {chain_id})")
    print_h_bar()
    
    # Call the API through the connection
    result = agent.connection_manager.perform_action(
        connection_name="api_tools",
        action_name="get-nft-holdings",
        params=[wallet_address, chain_id]
    )
    
    if result and "error" not in result:
        logger.info(f"\n✅ NFT holdings fetched for {wallet_address} on {network}:")
        print_h_bar()
        
        # Format and display the NFT holdings
        if "assets" in result and result["assets"]:
            logger.info("\nNFT Assets:")
            for idx, asset in enumerate(result["assets"], 1):
                logger.info(f"\nNFT #{idx}:")
                if isinstance(asset, dict):
                    # Display basic NFT information
                    if "name" in asset:
                        logger.info(f"  Name: {asset['name']}")
                    if "token_id" in asset:
                        logger.info(f"  Token ID: {asset['token_id']}")
                    if "asset_contract" in asset and isinstance(asset["asset_contract"], dict):
                        contract = asset["asset_contract"]
                        if "address" in contract:
                            logger.info(f"  Contract Address: {contract['address']}")
                        if "schema_name" in contract:
                            logger.info(f"  Standard: {contract['schema_name'].upper()}")
                    if "image_url" in asset:
                        logger.info(f"  Image URL: {asset['image_url']}")
                    if "provider" in asset:
                        logger.info(f"  Provider: {asset['provider']}")
                else:
                    logger.info(f"  {asset}")
            
            logger.info(f"\nTotal NFTs Found: {len(result['assets'])}")
        else:
            logger.info("\nNo NFTs found for this wallet address.")
        
        print_h_bar()
        return result
    else:
        error = result.get("error", "Unknown error") if result else "Failed to get NFT holdings"
        logger.error(f"\n❌ {error}")
        print_h_bar()
        return False

def detect_nft_holdings_query(text):
    """
    Detect if a user query is asking about NFT holdings.
    Returns a tuple of (wallet_address, network) if found, otherwise (None, None).
    """
    # Patterns to match NFT holdings queries
    nft_patterns = [
        r"(?:what|which|show|get|fetch|check) (?:nfts?|non-fungible tokens?)",
        r"nfts? (?:holdings?|owned|collection)",
        r"(?:owned|holding) nfts?",
        r"nft (?:collection|portfolio|gallery)",
        r"what nfts? (?:does|do) .* (?:have|own|hold)"
    ]
    
    # Pattern to match Ethereum addresses
    eth_address_pattern = r"0x[a-fA-F0-9]{40}"
    
    # Check if any NFT pattern matches
    is_nft_query = any(re.search(pattern, text.lower()) for pattern in nft_patterns)
    
    if not is_nft_query:
        return None, None
    
    # Try to extract wallet address
    wallet_match = re.search(eth_address_pattern, text)
    wallet_address = wallet_match.group(0) if wallet_match else None
    
    # Try to extract network
    network = None
    for net in NETWORK_TO_CHAIN_ID.keys():
        if net.lower() in text.lower():
            network = net
            break
    
    # Default to Ethereum if no specific network mentioned
    if not network:
        network = "ethereum"
    
    return wallet_address, network

@register_action("get-spot-price")
def get_spot_price(agent, **kwargs):
    """
    Action to get spot prices of whitelisted tokens in a specified currency.
    This will be triggered when the user asks about token prices.
    """
    # Get currency and chain_id from kwargs
    currency = kwargs.get("currency", "USD").upper()
    chain_id = kwargs.get("chain_id", "1")  # Default to Ethereum (1) if not provided
    
    # Find network name from chain ID for display
    network = "Ethereum"  # Default
    for net, cid in NETWORK_TO_CHAIN_ID.items():
        if cid == chain_id:
            network = net.capitalize()
            break
    
    logger.info(f"\n🔍 FETCHING SPOT PRICES IN {currency} FOR {network.upper()} (Chain ID: {chain_id})")
    print_h_bar()
    
    # Call the API through the connection
    result = agent.connection_manager.perform_action(
        connection_name="api_tools",
        action_name="get-spot-price",
        params=[currency, chain_id]
    )
    
    if result and "error" not in result:
        logger.info(f"\n✅ Spot prices fetched in {currency} for {network}:")
        
        # Log the raw response for debugging
        logger.info("\n📦 Raw Price Data:")
        import json
        logger.info(json.dumps(result, indent=2))
        
        # Simple summary of what was found
        token_count = len(result)
        logger.info(f"\nFound {token_count} token prices")
        
        print_h_bar()
        return result
    else:
        error = result.get("error", "Unknown error") if result else "Failed to get spot prices"
        logger.error(f"\n❌ {error}")
        print_h_bar()
        return False

def detect_spot_price_query(text):
    """
    Detect if a user query is asking about spot prices.
    Returns a tuple of (currency, network) if found, otherwise (None, None).
    """
    # Patterns to match spot price queries
    price_patterns = [
        r"(?:what(?:'s| is) the|current|check|get|show) (?:spot price|token price|price)",
        r"price (?:of|for) (?:tokens?|whitelisted tokens?)",
        r"token (?:price|value)",
        r"spot (?:price|value)"
    ]
    
    # Check if any price pattern matches
    is_price_query = any(re.search(pattern, text.lower()) for pattern in price_patterns)
    
    if not is_price_query:
        return None, None
    
    # List of supported currencies
    currencies = ["USD", "INR", "EUR", "GBP", "JPY", "CNY"]
    
    # Try to extract currency
    currency = "USD"  # Default
    for curr in currencies:
        if curr.lower() in text.lower():
            currency = curr
            break
    
    # Try to extract network
    network = None
    for net in NETWORK_TO_CHAIN_ID.keys():
        if net.lower() in text.lower():
            network = net
            break
    
    # Default to Ethereum if no specific network mentioned
    if not network:
        network = "ethereum"
    
    return currency, network

@register_action("get-token-value")
def get_token_value(agent, **kwargs):
    """
    Action to get the current value of a specific token by its address.
    This will be triggered when the user asks about a token's value.
    """
    # Check if token_address and chain_id are provided in kwargs
    token_address = kwargs.get("token_address")
    chain_id = kwargs.get("chain_id")
    network = kwargs.get("network")
    
    if not token_address:
        logger.error("\n❌ No token address provided")
        return False
    
    # If network name is provided, convert to chain_id
    if network and not chain_id:
        network = network.lower()
        chain_id = NETWORK_TO_CHAIN_ID.get(network)
        if not chain_id:
            logger.error(f"\n❌ Unknown network: {network}")
            return False
    
    # If no chain_id or network provided, default to Ethereum
    if not chain_id:
        chain_id = "1"  # Default to Ethereum
        network = "Ethereum"
    else:
        # Find network name from chain ID for display
        for net, cid in NETWORK_TO_CHAIN_ID.items():
            if cid == chain_id:
                network = net.capitalize()
                break
        else:
            network = f"Chain ID {chain_id}"
    
    logger.info(f"\n🔍 FETCHING TOKEN VALUE FOR {token_address} ON {network.upper()} (Chain ID: {chain_id})")
    logger.info(f"API Endpoint: https://api.1inch.dev/portfolio/portfolio/v4/overview/erc20/current_value")
    print_h_bar()
    
    # Call the API through the connection
    result = agent.connection_manager.perform_action(
        connection_name="api_tools",
        action_name="get-token-value",
        params=[token_address, chain_id]
    )
    
    if result and "error" not in result:
        logger.info(f"\n✅ Token value fetched for {token_address} on {network}:")
        
        # Log the raw response for debugging
        logger.info("\n📦 Raw Token Value Data:")
        import json
        logger.info(json.dumps(result, indent=2))
        
        # Extract and display the token value information
        if "result" in result:
            # Process the result to extract values
            total_value_usd = 0
            
            for protocol in result["result"]:
                protocol_name = protocol.get("protocol_name", "Unknown")
                
                for chain_result in protocol.get("result", []):
                    if chain_result.get("chain_id") == int(chain_id):
                        value_usd = chain_result.get("value_usd", 0)
                        logger.info(f"Protocol: {protocol_name}, Value: ${value_usd:,.2f} USD")
                        total_value_usd += value_usd
            
            logger.info(f"\nTotal Value: ${total_value_usd:,.2f} USD")
        
        print_h_bar()
        return result
    else:
        error = result.get("error", "Unknown error") if result else "Failed to get token value"
        logger.error(f"\n❌ {error}")
        print_h_bar()
        return False

def detect_token_value_query(text):
    """
    Detect if a user query is asking about a token's value.
    Returns a tuple of (token_address, network) if found, otherwise (None, None).
    """
    # First check if this is a token details query - if so, return None, None
    # to avoid misidentifying token details queries as token value queries
    token_details_patterns = [
        r"token details",
        r"get token details",
        r"(?:token|erc20) (?:details|info|information)"
    ]
    
    # If any token details pattern matches, this is not a token value query
    if any(re.search(pattern, text.lower()) for pattern in token_details_patterns):
        return None, None
    
    # Patterns to match token value queries - be more specific
    token_value_patterns = [
        r"(?:what(?:'s| is) the|current|check|get|show) (?:value|price|worth) of (?:token|erc20)",
        r"(?:token|erc20) (?:value|price|worth)",
        r"how much is (?:token|erc20) worth",
        r"value of (?:token|erc20)",
        r"current value",
        r"token value",
        r"token worth"
    ]
    
    # Pattern to match Ethereum addresses
    eth_address_pattern = r"0x[a-fA-F0-9]{40}"
    
    # Check if any token value pattern matches
    is_token_value_query = any(re.search(pattern, text.lower()) for pattern in token_value_patterns)
    
    # Also check if there's an ETH address in the query
    address_match = re.search(eth_address_pattern, text)
    
    if not (is_token_value_query or address_match):
        return None, None
    
    # If it's not explicitly a value query and just has an address, check for value-specific keywords
    if not is_token_value_query and address_match:
        value_keywords = ["value", "worth", "price", "cost", "how much"]
        if not any(keyword in text.lower() for keyword in value_keywords):
            return None, None
    
    # Try to extract token address
    token_address = address_match.group(0) if address_match else None
    
    # Try to extract network
    network = None
    for net in NETWORK_TO_CHAIN_ID.keys():
        if net.lower() in text.lower():
            network = net
            break
    
    # Default to Ethereum if no specific network mentioned
    if not network:
        network = "ethereum"
    
    # Log the detection for debugging
    logger.info(f"\n🔍 Detected token value query: {is_token_value_query}")
    logger.info(f"Token address: {token_address}")
    logger.info(f"Network: {network}")
    
    return token_address, network

@register_action("get-token-details")
def get_token_details(agent, **kwargs):
    """
    Action to get detailed information about a specific token by its address.
    This will be triggered when the user asks about token details.
    """
    # Check if token_address and chain_id are provided in kwargs
    token_address = kwargs.get("token_address")
    chain_id = kwargs.get("chain_id")
    network = kwargs.get("network")
    
    if not token_address:
        logger.error("\n❌ No token address provided")
        return False
    
    # If network name is provided, convert to chain_id
    if network and not chain_id:
        network = network.lower()
        chain_id = NETWORK_TO_CHAIN_ID.get(network)
        if not chain_id:
            logger.error(f"\n❌ Unknown network: {network}")
            return False
    
    # If no chain_id or network provided, default to Ethereum
    if not chain_id:
        chain_id = "1"  # Default to Ethereum
        network = "Ethereum"
    else:
        # Find network name from chain ID for display
        for net, cid in NETWORK_TO_CHAIN_ID.items():
            if cid == chain_id:
                network = net.capitalize()
                break
        else:
            network = f"Chain ID {chain_id}"
    
    logger.info(f"\n🔍 FETCHING TOKEN DETAILS FOR {token_address} ON {network.upper()} (Chain ID: {chain_id})")
    logger.info(f"API Endpoint: https://api.1inch.dev/portfolio/portfolio/v4/overview/erc20/details")
    print_h_bar()
    
    # Call the API through the connection
    result = agent.connection_manager.perform_action(
        connection_name="api_tools",
        action_name="get-token-details",
        params=[token_address, chain_id]
    )
    
    if result and "error" not in result:
        logger.info(f"\n✅ Token details fetched for {token_address} on {network}:")
        
        # Log the raw response for debugging
        logger.info("\n📦 Raw Token Details Data:")
        import json
        logger.info(json.dumps(result, indent=2))
        
        # Extract and display the token details information
        if "result" in result:
            # Process the result to extract token details
            for token_info in result["result"]:
                if token_info.get("chain_id") == int(chain_id) and token_info.get("contract_address") == token_address:
                    logger.info(f"\nToken Name: {token_info.get('name', 'Unknown')}")
                    logger.info(f"Symbol: {token_info.get('symbol', 'Unknown')}")
                    logger.info(f"Amount: {token_info.get('amount', 0):,.6f}")
                    logger.info(f"Price (USD): ${token_info.get('price_to_usd', 0):,.6f}")
                    logger.info(f"Value (USD): ${token_info.get('value_usd', 0):,.2f}")
                    
                    # Display ROI if available
                    if token_info.get('roi') is not None:
                        logger.info(f"ROI: {token_info.get('roi', 0) * 100:.2f}%")
                    
                    # Display profit/loss if available
                    if token_info.get('abs_profit_usd') is not None:
                        profit_usd = token_info.get('abs_profit_usd', 0)
                        profit_sign = "+" if profit_usd >= 0 else ""
                        logger.info(f"Profit/Loss: {profit_sign}${profit_usd:,.2f}")
        
        print_h_bar()
        return result
    else:
        error = result.get("error", "Unknown error") if result else "Failed to get token details"
        logger.error(f"\n❌ {error}")
        print_h_bar()
        return False

def detect_token_details_query(text):
    """
    Detect if a user query is asking about token details.
    Returns a tuple of (token_address, network) if found, otherwise (None, None).
    """
    # Patterns to match token details queries - be more specific
    token_details_patterns = [
        r"(?:what(?:'s| is| are)|tell me about|show|get|fetch|check) (?:the )?(?:token|erc20) (?:details|info|information)",
        r"(?:token|erc20) (?:details|info|information)",
        r"details (?:of|about|for) (?:token|erc20)",
        r"information (?:on|about) (?:token|erc20)",
        r"token details",
        r"get token details",
        r"detailed information"
    ]
    
    # Pattern to match Ethereum addresses
    eth_address_pattern = r"0x[a-fA-F0-9]{40}"
    
    # Check if any token details pattern matches
    is_token_details_query = any(re.search(pattern, text.lower()) for pattern in token_details_patterns)
    
    # Also check if there's an ETH address in the query
    address_match = re.search(eth_address_pattern, text)
    
    if not (is_token_details_query or address_match):
        return None, None
    
    # If it's not explicitly a details query and just has an address, check for details-specific keywords
    if not is_token_details_query and address_match:
        details_keywords = ["details", "info", "information", "stats", "statistics", "data"]
        if not any(keyword in text.lower() for keyword in details_keywords):
            return None, None
    
    # Try to extract token address
    token_address = address_match.group(0) if address_match else None
    
    # Try to extract network
    network = None
    for net in NETWORK_TO_CHAIN_ID.keys():
        if net.lower() in text.lower():
            network = net
            break
    
    # Default to Ethereum if no specific network mentioned
    if not network:
        network = "ethereum"
    
    # Log the detection for debugging
    logger.info(f"\n🔍 Detected token details query: {is_token_details_query}")
    logger.info(f"Token address: {token_address}")
    logger.info(f"Network: {network}")
    
    return token_address, network

@register_action("get-token-profitloss")
def get_token_profitloss(agent, **kwargs):
    """
    Action to get profit and loss information for a specific token by its address.
    This will be triggered when the user asks about a token's profit/loss.
    """
    # Check if token_address and chain_id are provided in kwargs
    token_address = kwargs.get("token_address")
    chain_id = kwargs.get("chain_id")
    network = kwargs.get("network")
    timerange = kwargs.get("timerange", "1day")  # Default to 1day if not provided
    
    if not token_address:
        logger.error("\n❌ No token address provided")
        return False
    
    # If network name is provided, convert to chain_id
    if network and not chain_id:
        network = network.lower()
        chain_id = NETWORK_TO_CHAIN_ID.get(network)
        if not chain_id:
            logger.error(f"\n❌ Unknown network: {network}")
            return False
    
    # If no chain_id or network provided, default to Ethereum
    if not chain_id:
        chain_id = "1"  # Default to Ethereum
        network = "Ethereum"
    else:
        # Find network name from chain ID for display
        for net, cid in NETWORK_TO_CHAIN_ID.items():
            if cid == chain_id:
                network = net.capitalize()
                break
        else:
            network = f"Chain ID {chain_id}"
    
    # Validate timerange
    valid_timeranges = ["1day", "7day", "30day", "90day", "180day", "365day", "all"]
    if timerange not in valid_timeranges:
        logger.warning(f"\n⚠️ Invalid timerange: {timerange}. Defaulting to 1day.")
        timerange = "1day"
    
    logger.info(f"\n🔍 FETCHING TOKEN PROFIT/LOSS FOR {token_address} ON {network.upper()} (Chain ID: {chain_id}, Timerange: {timerange})")
    logger.info(f"API Endpoint: https://api.1inch.dev/portfolio/portfolio/v4/overview/erc20/profit_and_loss")
    print_h_bar()
    
    # Call the API through the connection
    result = agent.connection_manager.perform_action(
        connection_name="api_tools",
        action_name="get-token-profitloss",
        params=[token_address, chain_id, timerange]
    )
    
    if result and "error" not in result:
        logger.info(f"\n✅ Token profit/loss fetched for {token_address} on {network} over {timerange}:")
        
        # Log the raw response for debugging
        logger.info("\n📦 Raw Token Profit/Loss Data:")
        import json
        logger.info(json.dumps(result, indent=2))
        
        # Extract and display the profit/loss information
        if "result" in result:
            # Process the result to extract profit/loss data
            for pl_info in result["result"]:
                if pl_info.get("chain_id") == int(chain_id) or pl_info.get("chain_id") is None:
                    abs_profit_usd = pl_info.get("abs_profit_usd", 0)
                    roi = pl_info.get("roi", 0) * 100  # Convert to percentage
                    
                    profit_sign = "+" if abs_profit_usd >= 0 else ""
                    logger.info(f"Absolute Profit/Loss: {profit_sign}${abs_profit_usd:,.2f} USD")
                    logger.info(f"ROI: {roi:.4f}%")
        
        print_h_bar()
        return result
    else:
        error = result.get("error", "Unknown error") if result else "Failed to get token profit/loss"
        logger.error(f"\n❌ {error}")
        print_h_bar()
        return False

def detect_token_profitloss_query(text):
    """
    Detect if a user query is asking about a token's profit/loss.
    Returns a tuple of (token_address, network, timerange) if found, otherwise (None, None, None).
    """
    # Patterns to match token profit/loss queries
    profitloss_patterns = [
        r"(?:what(?:'s| is) the|current|check|get|show) (?:profit|loss|profitloss|profit and loss|profit/loss|p&l|roi|return)",
        r"(?:token|erc20) (?:profit|loss|profitloss|profit and loss|profit/loss|p&l|roi|return)",
        r"how much (?:profit|loss|return) (?:for|from) (?:token|erc20)",
        r"(?:profit|loss|profitloss|profit and loss|profit/loss|p&l|roi|return) (?:of|for|from) (?:token|erc20)",
        r"(?:profit|loss|profitloss|profit and loss|profit/loss|p&l|roi|return) (?:information|data|stats|statistics)"
    ]
    
    # Pattern to match Ethereum addresses
    eth_address_pattern = r"0x[a-fA-F0-9]{40}"
    
    # Check if any profit/loss pattern matches
    is_profitloss_query = any(re.search(pattern, text.lower()) for pattern in profitloss_patterns)
    
    # Also check if there's an ETH address in the query
    address_match = re.search(eth_address_pattern, text)
    
    if not (is_profitloss_query or address_match):
        return None, None, None
    
    # If it's not explicitly a profit/loss query and just has an address, check for profit/loss-specific keywords
    if not is_profitloss_query and address_match:
        profitloss_keywords = ["profit", "loss", "profitloss", "roi", "return", "p&l", "gain"]
        if not any(keyword in text.lower() for keyword in profitloss_keywords):
            return None, None, None
    
    # Try to extract token address
    token_address = address_match.group(0) if address_match else None
    
    # Try to extract network
    network = None
    for net in NETWORK_TO_CHAIN_ID.keys():
        if net.lower() in text.lower():
            network = net
            break
    
    # Default to Ethereum if no specific network mentioned
    if not network:
        network = "ethereum"
    
    # Try to extract timerange
    timerange = "1day"  # Default
    timerange_patterns = {
        r"(?:1|one)[ -]?day": "1day",
        r"(?:7|seven)[ -]?day": "7day",
        r"(?:30|thirty)[ -]?day": "30day",
        r"(?:90|ninety)[ -]?day": "90day",
        r"(?:180|one hundred eighty)[ -]?day": "180day",
        r"(?:365|one year)[ -]?day": "365day",
        r"all[ -]?time": "all"
    }
    
    for pattern, value in timerange_patterns.items():
        if re.search(pattern, text.lower()):
            timerange = value
            break
    
    # Log the detection for debugging
    logger.info(f"\n🔍 Detected token profit/loss query: {is_profitloss_query}")
    logger.info(f"Token address: {token_address}")
    logger.info(f"Network: {network}")
    logger.info(f"Timerange: {timerange}")
    
    return token_address, network, timerange

@register_action("get-transaction-trace")
def get_transaction_trace(agent, **kwargs):
    """
    Action to get detailed trace information for a specific transaction.
    This will be triggered when the user asks about transaction traces.
    """
    # Check if tx_hash and block_number are provided in kwargs
    tx_hash = kwargs.get("tx_hash")
    block_number = kwargs.get("block_number")
    chain_id = kwargs.get("chain_id")
    network = kwargs.get("network")
    
    if not tx_hash:
        logger.error("\n❌ No transaction hash provided")
        return False
    
    if not block_number:
        logger.error("\n❌ No block number provided")
        return False
    
    # If network name is provided, convert to chain_id
    if network and not chain_id:
        network = network.lower()
        chain_id = NETWORK_TO_CHAIN_ID.get(network)
        if not chain_id:
            logger.error(f"\n❌ Unknown network: {network}")
            return False
    
    # If no chain_id or network provided, default to Ethereum
    if not chain_id:
        chain_id = "1"  # Default to Ethereum
        network = "Ethereum"
    else:
        # Find network name from chain ID for display
        for net, cid in NETWORK_TO_CHAIN_ID.items():
            if cid == chain_id:
                network = net.capitalize()
                break
        else:
            network = f"Chain ID {chain_id}"
    
    logger.info(f"\n🔍 FETCHING TRANSACTION TRACE FOR TX {tx_hash} IN BLOCK {block_number} ON {network.upper()} (Chain ID: {chain_id})")
    logger.info(f"API Endpoint: https://api.1inch.dev/traces/v1.0/chain/{chain_id}/block-trace/{block_number}/tx-hash/{tx_hash}")
    print_h_bar()
    
    # Call the API through the connection
    result = agent.connection_manager.perform_action(
        connection_name="api_tools",
        action_name="get-transaction-trace",
        params=[tx_hash, block_number]
    )
    
    if result and "error" not in result:
        logger.info(f"\n✅ Transaction trace fetched for TX {tx_hash} in block {block_number} on {network}:")
        
        # Log the raw response for debugging
        logger.info("\n📦 Raw Transaction Trace Data:")
        import json
        logger.info(json.dumps(result, indent=2))
        
        # Extract and display the transaction trace information
        if "transactionTrace" in result:
            trace = result["transactionTrace"]
            
            # Display basic transaction information
            logger.info("\nTransaction Information:")
            logger.info(f"Transaction Hash: {trace.get('txHash', 'Unknown')}")
            logger.info(f"From: {trace.get('from', 'Unknown')}")
            logger.info(f"To: {trace.get('to', 'Unknown')}")
            logger.info(f"Value: {trace.get('value', '0x0')}")
            logger.info(f"Gas Limit: {trace.get('gasLimit', 'Unknown')}")
            logger.info(f"Gas Used: {trace.get('gasUsed', 'Unknown')}")
            logger.info(f"Gas Price: {trace.get('gasPrice', 'Unknown')}")
            logger.info(f"Status: {trace.get('status', 'Unknown')}")
            
            # Display logs if available
            if "logs" in trace and trace["logs"]:
                logger.info("\nTransaction Logs:")
                for idx, log in enumerate(trace["logs"], 1):
                    logger.info(f"\nLog #{idx}:")
                    logger.info(f"Contract: {log.get('contract', 'Unknown')}")
                    logger.info(f"Data: {log.get('data', 'None')}")
                    if "topics" in log and log["topics"]:
                        logger.info("Topics:")
                        for topic_idx, topic in enumerate(log["topics"], 1):
                            logger.info(f"  {topic_idx}. {topic}")
            
            # Display calls if available
            if "calls" in trace and trace["calls"]:
                logger.info("\nInternal Calls:")
                for idx, call in enumerate(trace["calls"], 1):
                    logger.info(f"\nCall #{idx}:")
                    logger.info(f"Type: {call.get('type', 'Unknown')}")
                    logger.info(f"From: {call.get('from', 'Unknown')}")
                    logger.info(f"To: {call.get('to', 'Unknown')}")
                    logger.info(f"Value: {call.get('value', '0x0')}")
        
        print_h_bar()
        return result
    else:
        error = result.get("error", "Unknown error") if result else "Failed to get transaction trace"
        logger.error(f"\n❌ {error}")
        print_h_bar()
        return False

def detect_transaction_trace_query(text):
    """
    Detect if a user query is asking about transaction traces.
    Returns a tuple of (tx_hash, block_number, network) if found, otherwise (None, None, None).
    """
    # Patterns to match transaction trace queries
    trace_patterns = [
        r"(?:what(?:'s| is) the|get|fetch|show|find) (?:transaction trace|tx trace|trace)",
        r"(?:transaction|tx) (?:trace|details|information)",
        r"trace (?:of|for) (?:transaction|tx)",
        r"(?:trace|details) (?:of|for|about) (?:transaction|tx)",
        r"transaction (?:execution|call) (?:trace|details)"
    ]
    
    # Pattern to match transaction hashes
    tx_hash_pattern = r"0x[a-fA-F0-9]{64}"
    
    # Pattern to match block numbers
    block_number_pattern = r"(?:block|blk)(?:\s+(?:number|#|num|no))?(?:\s*[:=]\s*|\s+)(\d+)"
    block_number_simple_pattern = r"\b\d{7,}\b"  # Simple pattern for large numbers that might be block numbers
    
    # Check if any trace pattern matches
    is_trace_query = any(re.search(pattern, text.lower()) for pattern in trace_patterns)
    
    # Also check if there's a transaction hash in the query
    tx_hash_match = re.search(tx_hash_pattern, text)
    
    if not (is_trace_query or tx_hash_match):
        return None, None, None
    
    # Try to extract transaction hash
    tx_hash = tx_hash_match.group(0) if tx_hash_match else None
    
    # Try to extract block number
    block_number = None
    block_match = re.search(block_number_pattern, text)
    if block_match:
        block_number = block_match.group(1)
    else:
        # Try the simple pattern if the more specific one didn't match
        simple_match = re.search(block_number_simple_pattern, text)
        if simple_match:
            block_number = simple_match.group(0)
    
    # Try to extract network
    network = None
    for net in NETWORK_TO_CHAIN_ID.keys():
        if net.lower() in text.lower():
            network = net
            break
    
    # Default to Ethereum if no specific network mentioned
    if not network:
        network = "ethereum"
    
    # Log the detection for debugging
    logger.info(f"\n🔍 Detected transaction trace query: {is_trace_query}")
    logger.info(f"Transaction hash: {tx_hash}")
    logger.info(f"Block number: {block_number}")
    logger.info(f"Network: {network}")
    
    return tx_hash, block_number, network

@register_action("get-transaction-history")
def get_transaction_history(agent, **kwargs):
    """
    Action to get transaction history for a specific wallet address on a blockchain.
    This will be triggered when the user asks about a wallet's transaction history.
    """
    # Check if wallet_address and chain_id are provided in kwargs
    wallet_address = kwargs.get("wallet_address")
    chain_id = kwargs.get("chain_id")
    network = kwargs.get("network")
    
    if not wallet_address:
        logger.error("\n❌ No wallet address provided")
        return False
    
    # If network name is provided, convert to chain_id
    if network and not chain_id:
        network = network.lower()
        chain_id = NETWORK_TO_CHAIN_ID.get(network)
        if not chain_id:
            logger.error(f"\n❌ Unknown network: {network}")
            return False
    
    # If no chain_id or network provided, default to Ethereum
    if not chain_id:
        chain_id = "1"  # Default to Ethereum
        network = "Ethereum"
    else:
        # Find network name from chain ID for display
        for net, cid in NETWORK_TO_CHAIN_ID.items():
            if cid == chain_id:
                network = net.capitalize()
                break
        else:
            network = f"Chain ID {chain_id}"
    
    logger.info(f"\n🔍 FETCHING TRANSACTION HISTORY FOR {wallet_address} ON {network.upper()} (Chain ID: {chain_id})")
    logger.info(f"API Endpoint: https://api.1inch.dev/history/v2.0/history/{wallet_address}/events")
    print_h_bar()
    
    # Call the API through the connection
    result = agent.connection_manager.perform_action(
        connection_name="api_tools",
        action_name="get-transaction-history",
        params=[wallet_address, chain_id]
    )
    
    if result and "error" not in result:
        logger.info(f"\n✅ Transaction history fetched for {wallet_address} on {network}:")
        
        # Log the raw response for debugging
        logger.info("\n📦 Raw Transaction History Data:")
        import json
        logger.info(json.dumps(result, indent=2))
        
        # Format and display the transaction history information
        if "items" in result and result["items"]:
            logger.info(f"\nFound {len(result['items'])} transactions:")
            
            for idx, tx in enumerate(result["items"], 1):
                if "details" in tx:
                    details = tx["details"]
                    tx_hash = details.get("txHash", "Unknown")
                    tx_type = details.get("type", "Unknown")
                    status = details.get("status", "Unknown")
                    block_number = details.get("blockNumber", "Unknown")
                    from_addr = details.get("fromAddress", "Unknown")
                    to_addr = details.get("toAddress", "Unknown")
                    
                    logger.info(f"\nTransaction #{idx}:")
                    logger.info(f"Hash: {tx_hash}")
                    logger.info(f"Type: {tx_type}")
                    logger.info(f"Status: {status}")
                    logger.info(f"Block: {block_number}")
                    logger.info(f"From: {from_addr}")
                    logger.info(f"To: {to_addr}")
                    
                    # Display token actions if available
                    if "tokenActions" in details and details["tokenActions"]:
                        logger.info("\nToken Actions:")
                        for token_action in details["tokenActions"]:
                            token_addr = token_action.get("address", "Unknown")
                            token_std = token_action.get("standard", "Unknown")
                            token_amount = token_action.get("amount", "0")
                            token_direction = token_action.get("direction", "Unknown")
                            
                            logger.info(f"  Token: {token_addr}")
                            logger.info(f"  Standard: {token_std}")
                            logger.info(f"  Amount: {token_amount}")
                            logger.info(f"  Direction: {token_direction}")
        else:
            logger.info("\nNo transactions found for this wallet address.")
        
        print_h_bar()
        return result
    else:
        error = result.get("error", "Unknown error") if result else "Failed to get transaction history"
        logger.error(f"\n❌ {error}")
        print_h_bar()
        return False

def detect_transaction_history_query(text):
    """
    Detect if a user query is asking about transaction history.
    Returns a tuple of (wallet_address, network) if found, otherwise (None, None).
    """
    # Patterns to match transaction history queries
    history_patterns = [
        r"(?:what(?:'s| is| are)|show|get|fetch|check) (?:the )?(?:transaction|tx) (?:history|record|log)",
        r"(?:transaction|tx) (?:history|record|log)",
        r"(?:history|record|log) (?:of|for) (?:transaction|tx|wallet|address)",
        r"(?:past|recent|previous) (?:transaction|tx)",
        r"what (?:transaction|tx) (?:has|have) (?:wallet|address)",
        r"(?:list|show) (?:all|recent) (?:transaction|tx)"
    ]
    
    # Pattern to match Ethereum addresses
    eth_address_pattern = r"0x[a-fA-F0-9]{40}"
    
    # Check if any history pattern matches
    is_history_query = any(re.search(pattern, text.lower()) for pattern in history_patterns)
    
    # Also check if there's an ETH address in the query
    address_match = re.search(eth_address_pattern, text)
    
    if not (is_history_query or address_match):
        return None, None
    
    # If it's not explicitly a history query and just has an address, check for history-specific keywords
    if not is_history_query and address_match:
        history_keywords = ["history", "transactions", "tx", "record", "log", "activity"]
        if not any(keyword in text.lower() for keyword in history_keywords):
            return None, None
    
    # Try to extract wallet address
    wallet_address = address_match.group(0) if address_match else None
    
    # Try to extract network
    network = None
    for net in NETWORK_TO_CHAIN_ID.keys():
        if net.lower() in text.lower():
            network = net
            break
    
    # Default to Ethereum if no specific network mentioned
    if not network:
        network = "ethereum"
    
    # Log the detection for debugging
    logger.info(f"\n🔍 Detected transaction history query: {is_history_query}")
    logger.info(f"Wallet address: {wallet_address}")
    logger.info(f"Network: {network}")
    
    return wallet_address, network 