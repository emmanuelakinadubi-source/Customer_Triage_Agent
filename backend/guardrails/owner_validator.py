from dataclasses import dataclass


ALLOWED_OWNERS_BY_CATEGORY = {
    "Refund Request": {"Billing Team", "Customer Service Agent"},
    "Delivery Issue": {"Logistics Team", "Customer Service Agent"},
    "Product Complaint": {"Customer Service Agent", "Escalate to Manager"},
    "Account Problem": {"Billing Team", "Customer Service Agent"},
    "General Enquiry": {"Customer Service Agent"},
    "Compliment": {"Customer Service Agent"},
    "Other": {"Customer Service Agent", "Billing Team", "Logistics Team", "Escalate to Manager"},
}

HIGH_URGENCY_ESCALATION_CATEGORIES = {
    "Refund Request",
    "Product Complaint",
    "Account Problem",
}


@dataclass(frozen=True)
class OwnerValidationResult:
    valid: bool
    reason: str = "Owner is valid"


def validate_owner(category: str, owner: str, urgency: str = "Low") -> OwnerValidationResult:
    allowed_owners = ALLOWED_OWNERS_BY_CATEGORY.get(category)
    if allowed_owners is None:
        return OwnerValidationResult(False, f"Unknown category: {category}")

    if urgency == "High" and category in HIGH_URGENCY_ESCALATION_CATEGORIES:
        if owner != "Escalate to Manager":
            return OwnerValidationResult(
                False,
                f"High urgency {category} must be assigned to Escalate to Manager",
            )
        return OwnerValidationResult(True)

    if owner not in allowed_owners:
        allowed = ", ".join(sorted(allowed_owners))
        return OwnerValidationResult(
            False,
            f"{category} must be assigned to one of: {allowed}",
        )

    return OwnerValidationResult(True)
