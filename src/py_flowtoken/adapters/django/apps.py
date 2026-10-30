from pathlib import Path

from django.apps import AppConfig


class FlowTokenConfig(AppConfig):
    name = "py_flowtoken.adapters.django"
    label = "py_flowtoken"
    verbose_name = "Python FlowToken"
    path = str(Path(__file__).resolve().parents[2])
