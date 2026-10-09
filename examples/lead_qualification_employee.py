"""Run a no-cost, offline smoke test of the lead qualification employee.

This example uses a deterministic fake model. Replace it with a configured
ChatModel provider for actual AI conversations. It never calls an external API.
"""
from core.lead_qualification import LeadProfile, create_lead_qualification_employee, qualify_lead
from core.models import ModelResponse
from core.tool_registry import ToolRegistry


class DemoModel:
    def chat(self, messages, tools):
        return ModelResponse(content=(
            "Demo only: ask for the prospect's timeline next, then confirm whether "
            "they consent to follow-up. No CRM write or message was sent."
        ))


def main():
    employee = create_lead_qualification_employee(DemoModel(), ToolRegistry())
    response = employee.run_result(
        "A prospect wants a home, has a budget of ₹80 lakh, and hopes to move "
        "within three months. They have not given follow-up consent."
    )
    qualification = qualify_lead(LeadProfile(
        need="Wants a home",
        budget="₹80 lakh",
        timeline="Within three months",
        contact_method="",
        consent_to_contact=False,
    ))
    print("Employee status:", response.status)
    print("Employee response:", response.output)
    print("Qualification:", qualification)


if __name__ == "__main__":
    main()
