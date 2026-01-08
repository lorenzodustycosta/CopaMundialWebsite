from datetime import date
from tournament.services.knockout_service import KnockoutDates

"""
Centralized configuration for tournament knockout dates.
"""

KNOCKOUT_DATES = KnockoutDates(
    quarter_day1=date(2025, 7, 1),
    quarter_day2=date(2025, 7, 2),
    semi_day=date(2025, 7, 5),
    final_day=date(2025, 7, 7),
)

GROUP_STAGE_START_DATE = date(2025, 6, 3)
