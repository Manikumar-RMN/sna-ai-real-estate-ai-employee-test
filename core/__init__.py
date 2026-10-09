"""SNA AI Agent Engine public API."""

from .agent import Agent
from .employee import AIEmployee, EmployeeDefinition
from .config import AgentConfig, RuntimeContext
from .memory import ConversationMemory
from .models import AgentResult, ModelResponse, ToolCall
from .providers import FunctionModelProvider, ModelProvider
from .openai_provider import OpenAICompatibleProvider
from .store import InMemoryRunStore, JsonFileRunStore, RunStore
from .supabase_store import SupabaseRunStore
from .conversation_store import SupabaseConversationStore
from .knowledge import CompositeKnowledgeProvider, KnowledgeItem, KnowledgeProvider
from .knowledge_memory import InMemoryKnowledgeProvider
from .supabase_knowledge import SupabaseKnowledgeProvider
from .tool_registry import Tool, ToolRegistry
from .integrations import FunctionIntegration, IntegrationAdapter, IntegrationDescriptor, IntegrationHealth, IntegrationRegistry
from .integration_executor import IntegrationAction, IntegrationActionExecutor, IntegrationActionRegistry, IntegrationActionResult
from .integration_tools import integration_tool_bundle
from .mock_crm import MockCRM, register_mock_crm
from .secure_http import (HttpResponse, InMemorySecretProvider, IntegrationRequestError, SecretProvider, TenantScopedHttpJsonClient, UrllibHttpTransport)
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
    "IntegrationAction",
    "IntegrationActionRegistry",
    "IntegrationActionExecutor",
    "IntegrationActionResult",
    "integration_tool_bundle",
    "MockCRM",
    "register_mock_crm",
    "ToolBundle",
    "ToolSet",
    "standard_tool_bundle",
    "SecretProvider",
    "InMemorySecretProvider",
    "HttpResponse",
    "IntegrationRequestError",
    "TenantScopedHttpJsonClient",
    "UrllibHttpTransport",
]
