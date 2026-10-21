"""Saved-data analysis, with lazy notebook plotting exports."""

from importlib import import_module

__all__ = ["RunRegistry", "NotebookPlots", "FigureStyle", "WilsonInterval"]


def __getattr__(name):
    modules = {"RunRegistry": "saved_data", "NotebookPlots": "notebook_plotting",
               "FigureStyle": "figure_style", "WilsonInterval": "confidence"}
    if name not in modules:
        raise AttributeError(name)
    value = getattr(import_module(f".{modules[name]}", __name__), name)
    globals()[name] = value
    return value
