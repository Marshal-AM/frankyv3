import logging
from typing import Any, List, Optional, Dict
from src.connections.ollama_connection import OllamaConnection
from src.connections.api_tools_connection import APIToolsConnection

logger = logging.getLogger("connection_manager")

class BaseConnection:
    def __init__(self, config):
        self.config = config
        self.actions = {}

    def is_configured(self, verbose=False):
        raise NotImplementedError("Subclasses must implement is_configured")

    def configure(self):
        raise NotImplementedError("Subclasses must implement configure")

    def perform_action(self, action_name, kwargs):
        raise NotImplementedError("Subclasses must implement perform_action")

class ConnectionManager:
    def __init__(self, agent_config):
        self.connections: Dict[str, BaseConnection] = {}
        for config in agent_config:
            self._register_connection(config)

    def _class_name_to_type(self, class_name: str):
        connection_map = {
            "ollama": OllamaConnection,
            "api_tools": APIToolsConnection
        }
        return connection_map.get(class_name)

    def _register_connection(self, config_dic: Dict[str, Any]) -> None:
        try:
            name = config_dic["name"]
            connection_class = self._class_name_to_type(name)
            if connection_class:
                connection = connection_class(config_dic)
                self.connections[name] = connection
            else:
                logger.error(f"Unsupported connection type: {name}")
        except Exception as e:
            logger.error(f"Failed to initialize connection {config_dic.get('name', 'unknown')}: {e}")

    def list_connections(self) -> None:
        logger.info("\nAVAILABLE CONNECTIONS:")
        for name, connection in self.connections.items():
            status = "✅ Configured" if connection.is_configured() else "❌ Not Configured"
            logger.info(f"- {name}: {status}")

    def list_actions(self, connection_name: str) -> None:
        try:
            connection = self.connections[connection_name]
            logger.info(f"\nACTIONS for {connection_name}:")
            for action_name, action in connection.actions.items():
                logger.info(f"- {action_name}: {action.description}")
        except KeyError:
            logger.error(f"Unknown connection: {connection_name}")

    def perform_action(
        self, connection_name: str, action_name: str, params: List[Any]
    ) -> Optional[Any]:
        try:
            connection = self.connections[connection_name]
            
            if not connection.is_configured():
                logger.error(f"Connection '{connection_name}' is not configured")
                return None

            # Special handling for Ollama chat action
            if connection_name == "ollama" and action_name == "chat":
                if params and isinstance(params[0], str):
                    params = [{"role": "user", "content": params[0]}]

            return connection.perform_action(action_name, params)

        except Exception as e:
            logger.error(f"Error in perform_action for {connection_name}: {e}")
            return None
