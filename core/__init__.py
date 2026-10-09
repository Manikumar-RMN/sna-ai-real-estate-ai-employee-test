"""SNA AI Agent Engine public API."""

from .agent import Agent
from .employee import AIEmployee, EmployeeDefinition
from .config import AgentConfig, RuntimeContext
from .memory import ConversationMemory
from .models import AgentResult, ModelResponse, ToolCall
from .providers import FunctionModelProvider, ModelProvider
from .store import InMemoryRunStore, JsonFileRunStore, RunStore
from .supabase_store import SupabaseRunStore
from .conversation_store import SupabaseConversationStore
from .knowledge import CompositeKnowledgeProvider, KnowledgeItem, KnowledgeProvider
from .knowledge_memory import InMemoryKnowledgeProvider
from .supabase_knowledge import SupabaseKnowledgeProvider
from .tool_registry import Tool, ToolRegistry
from .integrations import FunctionIntegration, IntegrationAdapter, IntegrationDescriptor, IntegrationHealth, IntegrationRegistry
from .tool_bundles import ToolBundle, ToolSet
from .standard_tools import standard_tool_bundle

__all__ = [
    "Agent",
    "AIEmployee",
    "EmployeeDefinition",
    "AgentConfig",
    "RuntimeContext",
    "ConversationMemory",
    "AgentResult",
    "ModelResponse",
    "ToolCall",
    "ModelProvider",
    "FunctionModelProvider",
    "RunStore",
    "InMemoryRunStore",
    "JsonFileRunStore",
    "SupabaseRunStore",
    "SupabaseConversationStore",
    "KnowledgeItem",
    "KnowledgeProvider",
    "CompositeKnowledgeProvider",
    "InMemoryKnowledgeProvider",
    "SupabaseKnowledgeProvider",
    "OpenAICompatibleProvider",
    "Tool",
    "ToolRegistry",
    "IntegrationAdapter",
    "IntegrationDescriptor",
    "IntegrationHealth",
    "IntegrationRegistry",
    "FunctionIntegration",
    "ToolBundle",
    "ToolSet",
    "standard_tool_bundle",
]
