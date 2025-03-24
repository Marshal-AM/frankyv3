import logging
import os
import requests
import json
from typing import Dict, Any
from dotenv import load_dotenv, set_key
from src.connections.base_connection import BaseConnection, Action, ActionParameter

logger = logging.getLogger("connections.api_tools_connection")

class APIToolsConnectionError(Exception):
    """Base exception for API Tools connection errors"""
    pass

class APIToolsConnection(BaseConnection):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Make sure environment variables are loaded
        load_dotenv()
        # Get API key from config or environment
        api_key_from_config = config.get("api_key", "")
        api_key_from_env = os.getenv("ONEINCH_API_KEY", "")
        
        # Prioritize config value over env if provided
        if api_key_from_config:
            self.api_key = api_key_from_config
        else:
            self.api_key = api_key_from_env
            
        # Check if API key is valid (not the placeholder)
        if self.api_key == "your_api_key_here":
            self.api_key = ""
            
        # Log API key status (masked)
        if self.api_key:
            mask = self.api_key[:4] + "..." + self.api_key[-4:] if len(self.api_key) > 8 else "****"
            logger.info(f"Initialized API Tools connection with API key: {mask}")
        else:
            logger.warning("API Tools connection initialized without API key. Some features may not work.")
            
        # Register the available actions
        self.register_actions()

    @property
    def is_llm_provider(self) -> bool:
        return False

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate API Tools configuration from JSON"""
        # API key is optional in config as it can be in .env
        return config

    def register_actions(self) -> None:
        """Register available API Tools actions"""
        self.actions = {
            "get-gas-price": Action(
                name="get-gas-price",
                parameters=[
                    ActionParameter("chain_id", True, str, "Chain ID (e.g., 1 for Ethereum, 56 for BSC)")
                ],
                description="Get current gas price for a specific blockchain network"
            ),
            "get-transaction-history": Action(
                name="get-transaction-history",
                parameters=[
                    ActionParameter("wallet_address", True, str, "Wallet address to fetch transactions for"),
                    ActionParameter("chain_id", True, str, "Chain ID (e.g., 1 for Ethereum, 56 for BSC)")
                ],
                description="Get transaction history for a specific wallet address"
            ),
            "get-nft-holdings": Action(
                name="get-nft-holdings",
                parameters=[
                    ActionParameter("wallet_address", True, str, "Wallet address to fetch NFTs for"),
                    ActionParameter("chain_id", True, str, "Chain ID (e.g., 1 for Ethereum, 56 for BSC)")
                ],
                description="Get NFT holdings for a specific wallet address"
            ),
            "get-spot-price": Action(
                name="get-spot-price",
                parameters=[
                    ActionParameter("currency", True, str, "Currency code (e.g., USD, INR, EUR)"),
                    ActionParameter("chain_id", False, str, "Chain ID (e.g., 1 for Ethereum, 56 for BSC, 43114 for Avalanche)")
                ],
                description="Get spot prices of whitelisted tokens in specified currency for a blockchain"
            ),
            "get-token-value": Action(
                name="get-token-value",
                parameters=[
                    ActionParameter("token_address", True, str, "Token contract address"),
                    ActionParameter("chain_id", False, str, "Chain ID (e.g., 1 for Ethereum, 56 for BSC)")
                ],
                description="Get current value of a specific token by its address"
            ),
            "get-token-details": Action(
                name="get-token-details",
                parameters=[
                    ActionParameter("token_address", True, str, "Token contract address"),
                    ActionParameter("chain_id", False, str, "Chain ID (e.g., 1 for Ethereum, 56 for BSC)")
                ],
                description="Get detailed information about a specific token by its address"
            ),
            "get-token-profitloss": Action(
                name="get-token-profitloss",
                parameters=[
                    ActionParameter("token_address", True, str, "Token contract address"),
                    ActionParameter("chain_id", False, str, "Chain ID (e.g., 1 for Ethereum, 56 for BSC)"),
                    ActionParameter("timerange", False, str, "Time range for profit/loss calculation (e.g., 1day, 7day, 30day)")
                ],
                description="Get profit and loss information for a specific token by its address"
            ),
            "get-transaction-trace": Action(
                name="get-transaction-trace",
                parameters=[
                    ActionParameter("tx_hash", True, str, "Transaction hash to fetch trace for"),
                    ActionParameter("block_number", True, str, "Block number containing the transaction")
                ],
                description="Get detailed trace information for a specific transaction"
            )
        }

    def configure(self) -> bool:
        """Configure API Tools connection"""
        logger.info("\n🔧 API TOOLS CONFIGURATION")
        
        # First check if we have API key already from .env
        existing_api_key = os.getenv("ONEINCH_API_KEY", "")
        if existing_api_key and existing_api_key != "your_api_key_here":
            self.api_key = existing_api_key
            logger.info("\n✅ Found existing 1inch API key in .env file.")
            mask = existing_api_key[:4] + "..." + existing_api_key[-4:] if len(existing_api_key) > 8 else "****"
            logger.info(f"Current API key (masked): {mask}")
            if input("\nWould you like to update your 1inch API key? (y/n): ").lower() != 'y':
                logger.info("\n✓ Using existing 1inch API key.")
                return True
        
        # If no existing key or user wants to update it
        logger.info("\n1. Sign up for a free 1inch API at https://portal.1inch.dev/")
        logger.info("2. After registration, create a new API key for Gas Price Service")
        logger.info("3. Copy your API key from the 1inch Developer Portal")
        
        api_key = input("\nEnter your 1inch API key: ").strip()
        
        if not api_key:
            logger.error("\n❌ No API key provided. APIs requiring authentication will not work.")
            return False
        
        # Save to .env file
        set_key('.env', 'ONEINCH_API_KEY', api_key)
        self.api_key = api_key
        
        logger.info("\n✅ API key saved successfully!")
        logger.info("Testing API connection...")
        
        # Test the API connection
        test_result = self.get_gas_price("1")  # Test with Ethereum (chain ID 1)
        if "error" not in test_result:
            logger.info("\n✅ API connection test successful!")
            return True
        else:
            logger.error(f"\n❌ API connection test failed: {test_result.get('error')}")
            logger.error("Please check your API key and try again.")
            return False

    def is_configured(self, verbose=False) -> bool:
        """Check if API Tools is configured"""
        load_dotenv()
        api_key = self.api_key or os.getenv("ONEINCH_API_KEY", "")
        
        if not api_key and verbose:
            logger.error("\n❌ API key not found. Please configure API Tools.")
            return False
        
        return bool(api_key)

    def get_gas_price(self, chain_id: str, **kwargs) -> Dict[str, Any]:
        """Get current gas price for a specific blockchain network"""
        try:
            api_url = f"https://api.1inch.dev/gas-price/v1.5/{chain_id}"
            
            # Check if API key is available
            if not self.api_key:
                logger.error("\n❌ No API key found for 1inch API. Please set ONEINCH_API_KEY in your .env file.")
                return {"error": "No API key found. Please configure ONEINCH_API_KEY."}
            
            # Log request details for debugging
            logger.info("\n📡 API Request Details:")
            logger.info(f"URL: {api_url}")
            logger.info(f"API Key (partial): {self.api_key[:4]}...{self.api_key[-4:] if len(self.api_key) > 8 else ''}")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            
            logger.info(f"Headers: {headers}")
            
            response = requests.get(api_url, headers=headers)
            
            # Log response details
            logger.info("\n📥 API Response Details:")
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                error_msg = f"Gas price request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                # Provide specific guidance for different error codes
                if response.status_code == 401:
                    logger.error("\n❌ Authentication failed. Your API key may be invalid or expired.")
                    logger.error("Please update your ONEINCH_API_KEY in the .env file.")
                    # Try to fetch from environment again, in case it was updated
                    env_api_key = os.getenv("ONEINCH_API_KEY", "")
                    if env_api_key != self.api_key:
                        logger.info("\n🔄 Detected different API key in environment, trying with updated key...")
                        self.api_key = env_api_key
                        return self.get_gas_price(chain_id, **kwargs)
                    
                return {"error": error_msg}
            
            # Parse and log the successful response data
            data = response.json()
            logger.info(f"\n✅ Got gas price data: {json.dumps(data, indent=2)}")
            return data
            
        except Exception as e:
            error_msg = f"Error getting gas price: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_transaction_history(self, wallet_address: str, chain_id: str, **kwargs) -> Dict[str, Any]:
        """Get transaction history for a specific wallet address"""
        try:
            api_url = f"https://api.1inch.dev/history/v2.0/history/{wallet_address}/events"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            params = {
                "chainId": chain_id
            }
            
            # Log request details
            logger.info("\n📡 API Request Details:")
            logger.info(f"URL: {api_url}")
            logger.info("Headers: Authorization: Bearer ***[API_KEY_HIDDEN]***")
            logger.info(f"Parameters: {params}")
            
            response = requests.get(api_url, headers=headers, params=params)
            
            # Log response details
            logger.info("\n📥 API Response Details:")
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                error_msg = f"Transaction history request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            response_data = response.json()
            
            # Log the raw response data
            logger.info("\n📦 Raw Response Data:")
            logger.info(json.dumps(response_data, indent=2))
            logger.info("\n" + "-" * 80 + "\n")
            
            # Log response summary
            logger.info("\n📊 Response Summary:")
            if "items" in response_data:
                logger.info(f"Items Found: {len(response_data['items'])}")
            if "cache_counter" in response_data:
                logger.info(f"Cache Counter: {response_data['cache_counter']}")
            
            return response_data
            
        except Exception as e:
            error_msg = f"Error getting transaction history: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_nft_holdings(self, wallet_address: str, chain_id: str, **kwargs) -> Dict[str, Any]:
        """Get NFT holdings for a specific wallet address"""
        try:
            api_url = "https://api.1inch.dev/nft/v2/byaddress"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            params = {
                "chainIds": [chain_id],
                "address": wallet_address
            }
            
            # Log request details
            logger.info("\n📡 NFT Holdings API Request:")
            logger.info(f"URL: {api_url}")
            logger.info("Headers: Authorization: Bearer ***[API_KEY_HIDDEN]***")
            logger.info(f"Parameters: {params}")
            
            response = requests.get(api_url, headers=headers, params=params)
            
            # Log response details
            logger.info("\n📥 API Response Details:")
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                error_msg = f"NFT holdings request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Log the raw response data
            logger.info("\n📦 Raw Response Data:")
            response_data = response.json()
            logger.info(json.dumps(response_data, indent=2))
            logger.info("\n" + "-" * 80 + "\n")
            
            return response_data
            
        except Exception as e:
            error_msg = f"Error getting NFT holdings: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_spot_price(self, currency: str, chain_id: str = "1", **kwargs) -> Dict[str, Any]:
        """Get spot prices of whitelisted tokens in specified currency for a specific blockchain"""
        try:
            api_url = f"https://api.1inch.dev/price/v1.1/{chain_id}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            params = {
                "currency": currency
            }
            
            # Log request details
            logger.info("\n📡 Spot Price API Request:")
            logger.info(f"URL: {api_url}")
            logger.info("Headers: Authorization: Bearer ***[API_KEY_HIDDEN]***")
            logger.info(f"Parameters: {params}")
            logger.info(f"Chain ID: {chain_id}")
            
            response = requests.get(api_url, headers=headers, params=params)
            
            # Log response details
            logger.info("\n📥 API Response Details:")
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                error_msg = f"Spot price request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Log the raw response data
            logger.info("\n📦 Raw Response Data:")
            response_data = response.json()
            logger.info(json.dumps(response_data, indent=2))
            logger.info("\n" + "-" * 80 + "\n")
            
            return response_data
            
        except Exception as e:
            error_msg = f"Error getting spot prices: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_token_value(self, token_address: str, chain_id: str = "1", **kwargs) -> Dict[str, Any]:
        """Get current value of a specific token by its address"""
        try:
            api_url = "https://api.1inch.dev/portfolio/portfolio/v4/overview/erc20/current_value"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            params = {
                "addresses": [token_address],
                "chain_id": chain_id,
                "use_cache": "false"
            }
            
            # Log request details
            logger.info("\n📡 Token Value API Request:")
            logger.info(f"URL: {api_url}")
            logger.info("Headers: Authorization: Bearer ***[API_KEY_HIDDEN]***")
            logger.info(f"Parameters: {params}")
            logger.info(f"Token Address: {token_address}")
            logger.info(f"Chain ID: {chain_id}")
            
            response = requests.get(api_url, headers=headers, params=params)
            
            # Log response details
            logger.info("\n📥 API Response Details:")
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                error_msg = f"Token value request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Log the raw response data
            logger.info("\n📦 Raw Response Data:")
            response_data = response.json()
            logger.info(json.dumps(response_data, indent=2))
            logger.info("\n" + "-" * 80 + "\n")
            
            return response_data
            
        except Exception as e:
            error_msg = f"Error getting token value: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_token_details(self, token_address: str, chain_id: str = "1", **kwargs) -> Dict[str, Any]:
        """Get detailed information about a specific token by its address"""
        try:
            api_url = "https://api.1inch.dev/portfolio/portfolio/v4/overview/erc20/details"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            params = {
                "addresses": [token_address],
                "chain_id": chain_id,
                "timerange": "1day",
                "closed": True,
                "closed_threshold": 1
            }
            
            # Log request details
            logger.info("\n📡 Token Details API Request:")
            logger.info(f"URL: {api_url}")
            logger.info("Headers: Authorization: Bearer ***[API_KEY_HIDDEN]***")
            logger.info(f"Parameters: {params}")
            logger.info(f"Token Address: {token_address}")
            logger.info(f"Chain ID: {chain_id}")
            
            response = requests.get(api_url, headers=headers, params=params)
            
            # Log response details
            logger.info("\n📥 API Response Details:")
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                error_msg = f"Token details request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Log the raw response data
            logger.info("\n📦 Raw Response Data:")
            response_data = response.json()
            logger.info(json.dumps(response_data, indent=2))
            logger.info("\n" + "-" * 80 + "\n")
            
            return response_data
            
        except Exception as e:
            error_msg = f"Error getting token details: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_token_profitloss(self, token_address: str, chain_id: str = "1", timerange: str = "1day", **kwargs) -> Dict[str, Any]:
        """Get profit and loss information for a specific token by its address"""
        try:
            api_url = "https://api.1inch.dev/portfolio/portfolio/v4/overview/erc20/profit_and_loss"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            params = {
                "addresses": [token_address],
                "chain_id": chain_id,
                "timerange": timerange,
                "use_cache": "false"
            }
            
            # Log request details
            logger.info("\n📡 Token Profit/Loss API Request:")
            logger.info(f"URL: {api_url}")
            logger.info("Headers: Authorization: Bearer ***[API_KEY_HIDDEN]***")
            logger.info(f"Parameters: {params}")
            logger.info(f"Token Address: {token_address}")
            logger.info(f"Chain ID: {chain_id}")
            logger.info(f"Time Range: {timerange}")
            
            response = requests.get(api_url, headers=headers, params=params)
            
            # Log response details
            logger.info("\n📥 API Response Details:")
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                error_msg = f"Token profit/loss request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Log the raw response data
            logger.info("\n📦 Raw Response Data:")
            response_data = response.json()
            logger.info(json.dumps(response_data, indent=2))
            logger.info("\n" + "-" * 80 + "\n")
            
            return response_data
            
        except Exception as e:
            error_msg = f"Error getting token profit/loss: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_transaction_trace(self, tx_hash: str, block_number: str, **kwargs) -> Dict[str, Any]:
        """Get detailed trace information for a specific transaction"""
        try:
            # Default to Ethereum mainnet (chain_id=1)
            chain_id = kwargs.get("chain_id", "1")
            
            api_url = f"https://api.1inch.dev/traces/v1.0/chain/{chain_id}/block-trace/{block_number}/tx-hash/{tx_hash}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Log request details
            logger.info("\n📡 Transaction Trace API Request:")
            logger.info(f"URL: {api_url}")
            logger.info("Headers: Authorization: Bearer ***[API_KEY_HIDDEN]***")
            logger.info(f"Transaction Hash: {tx_hash}")
            logger.info(f"Block Number: {block_number}")
            logger.info(f"Chain ID: {chain_id}")
            
            response = requests.get(api_url, headers=headers)
            
            # Log response details
            logger.info("\n📥 API Response Details:")
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                error_msg = f"Transaction trace request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Log the raw response data
            logger.info("\n📦 Raw Response Data:")
            response_data = response.json()
            logger.info(json.dumps(response_data, indent=2))
            logger.info("\n" + "-" * 80 + "\n")
            
            return response_data
            
        except Exception as e:
            error_msg = f"Error getting transaction trace: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def perform_action(self, action_name: str, kwargs) -> Any:
        """Perform a registered action with the given parameters"""
        if action_name == "get-gas-price":
            return self.get_gas_price(**kwargs)
        elif action_name == "get-transaction-history":
            return self.get_transaction_history(**kwargs)
        elif action_name == "get-nft-holdings":
            return self.get_nft_holdings(**kwargs)
        elif action_name == "get-spot-price":
            return self.get_spot_price(**kwargs)
        elif action_name == "get-token-value":
            return self.get_token_value(**kwargs)
        elif action_name == "get-token-details":
            return self.get_token_details(**kwargs)
        elif action_name == "get-token-profitloss":
            return self.get_token_profitloss(**kwargs)
        elif action_name == "get-transaction-trace":
            return self.get_transaction_trace(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action_name}") 