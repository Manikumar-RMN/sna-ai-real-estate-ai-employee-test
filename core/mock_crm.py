"""In-memory CRM integration for safe local development and tests.

This adapter is intentionally ephemeral and has no network or database access.
Do not use it as a production customer-data store.
"""
from typing import Any, Dict, Optional

from .integration_executor import IntegrationAction, IntegrationActionRegistry
from .integrations import FunctionIntegration, IntegrationDescriptor, IntegrationRegistry


class MockCRM:
    def __init__(self, contacts: Optional[list[dict[str, Any]]] = None) -> None:
        self._contacts: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1
        for contact in contacts or [
            {"id": "c-100", "name": "Asha Kumar", "email": "asha@example.test", "phone": "+910000000001"},
            {"id": "c-101", "name": "Ravi Shah", "email": "ravi@example.test", "phone": "+910000000002"},
        ]:
            self._contacts[contact["id"]] = dict(contact)
        self._next_id = len(self._contacts) + 100

    def search_contacts(self, query: str) -> dict[str, Any]:
        term = query.casefold()
        matches = [
            dict(contact) for contact in self._contacts.values()
            if term in contact["name"].casefold() or term in contact["email"].casefold()
        ]
        return {"contacts": matches, "count": len(matches)}

    def get_contact(self, contact_id: str) -> dict[str, Any]:
        contact = self._contacts.get(contact_id)
        if contact is None:
            raise ValueError("contact not found")
        return dict(contact)

    def create_contact(self, name: str, email: str, phone: Optional[str] = None) -> dict[str, Any]:
        contact_id = f"c-{self._next_id}"
        self._next_id += 1
        contact = {"id": contact_id, "name": name, "email": email, "phone": phone}
        self._contacts[contact_id] = contact
        return dict(contact)

    def update_contact(
        self, contact_id: str, name: Optional[str] = None,
        email: Optional[str] = None, phone: Optional[str] = None,
    ) -> dict[str, Any]:
        contact = self._contacts.get(contact_id)
        if contact is None:
            raise ValueError("contact not found")
        for key, value in (("name", name), ("email", email), ("phone", phone)):
            if value is not None:
                contact[key] = value
        return dict(contact)


def register_mock_crm(
    integrations: IntegrationRegistry,
    actions: IntegrationActionRegistry,
    crm: Optional[MockCRM] = None,
) -> MockCRM:
    """Register a local CRM and its explicitly allowed actions."""
    crm = crm or MockCRM()
    integrations.register(FunctionIntegration(IntegrationDescriptor(
        name="mock_crm",
        version="1.0",
        description="Ephemeral in-memory CRM for development and tests.",
        capabilities=("contacts.read", "contacts.write"),
        metadata={"environment": "mock"},
    )))
    actions.register("mock_crm", IntegrationAction(
        name="search_contacts",
        description="Search mock CRM contacts by name or email.",
        schema={
            "type": "object",
            "properties": {"query": {"type": "string", "minLength": 1}},
            "required": ["query"],
            "additionalProperties": False,
        },
        handler=crm.search_contacts,
        permission="read",
        capability="contacts.read",
    ))
    actions.register("mock_crm", IntegrationAction(
        name="get_contact",
        description="Get a mock CRM contact by ID.",
        schema={
            "type": "object",
            "properties": {"contact_id": {"type": "string", "minLength": 1}},
            "required": ["contact_id"],
            "additionalProperties": False,
        },
        handler=crm.get_contact,
        permission="read",
        capability="contacts.read",
    ))
    actions.register("mock_crm", IntegrationAction(
        name="create_contact",
        description="Create a contact in the in-memory mock CRM.",
        schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "email": {"type": "string", "format": "email"},
                "phone": {"type": ["string", "null"]},
            },
            "required": ["name", "email"],
            "additionalProperties": False,
        },
        handler=crm.create_contact,
        permission="write",
        capability="contacts.write",
    ))
    actions.register("mock_crm", IntegrationAction(
        name="update_contact",
        description="Update a contact in the in-memory mock CRM.",
        schema={
            "type": "object",
            "properties": {
                "contact_id": {"type": "string", "minLength": 1},
                "name": {"type": "string", "minLength": 1},
                "email": {"type": "string", "format": "email"},
                "phone": {"type": "string"},
            },
            "required": ["contact_id"],
            "minProperties": 2,
            "additionalProperties": False,
        },
        handler=crm.update_contact,
        permission="write",
        capability="contacts.write",
    ))
    return crm
