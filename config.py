"""Shared campus, category, and sheet settings for the BDU Student Union system."""

SHEET_NAME = "Complaints"

CAMPUSES = [
    "Peda",
    "Poly / BiT",
    "Zenzelma",
    "Sebatamit",
    "Tibebe Ghion",
    "Fashion Technology (Selam)",
    "Yibab",
]

CATEGORIES = [
    "Cafeteria",
    "Dorm",
    "Academic & Technology",
    "Peace & Security",
    "Other",
]

STATUSES = ["Open", "In Progress", "Resolved"]
PRIORITIES = ["Low", "Medium", "High"]

SHEET_HEADERS = [
    "Ticket ID",
    "Timestamp",
    "Campus",
    "Category",
    "Description",
    "Location",
    "Photo URL",
    "Anonymous",
    "Name",
    "Phone",
    "Department",
    "Status",
    "Priority",
    "Telegram User ID",
]
