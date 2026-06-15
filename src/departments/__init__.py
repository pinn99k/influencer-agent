"""Department registry — maps department names to classes."""
from departments.planning import PlanningDepartment

DEPARTMENT_CLASSES = [
    PlanningDepartment,
]


def get_department_order() -> list[str]:
    return [cls.display_name for cls in DEPARTMENT_CLASSES]
