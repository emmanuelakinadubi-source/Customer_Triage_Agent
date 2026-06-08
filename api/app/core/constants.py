# Placeholder file for the initial scaffold.
from typing import Dict, List

ALLOWED_CATEGORIES = [
    "Refund Request", 
    "Delivery Issue", 
    "Product Complaint", 
    "Account Problem", 
    "General Enquiry", 
    "Compliment", 
    "Other"
]

ALLOWED_URGENCIES = ["High", "Medium", "Low"]
ALLOWED_SENTIMENTS = ["Positive", "Negative", "Neutral", "Mixed"]
ALLOWED_OWNERS = ["Customer Service Agent", "Billing Team", "Logistics Team", "Escalate to Manager"]

ROUTING_RULES: Dict[str, List[str]] = {
    "Refund Request": ["Billing Team", "Customer Service Agent"],
    "Delivery Issue": ["Logistics Team", "Customer Service Agent"],
    "Product Complaint": ["Customer Service Agent", "Escalate to Manager"],
    "Account Problem": ["Billing Team", "Customer Service Agent"],
    "General Enquiry": ["Customer Service Agent"],
    "Compliment": ["Customer Service Agent"],
    "Other": ALLOWED_OWNERS
}