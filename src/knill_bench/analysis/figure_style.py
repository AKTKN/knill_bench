"""Central publication style supplied by the user's plotting_lib package."""

from contextlib import contextmanager
from dataclasses import dataclass, field

import matplotlib as mpl
import matplotlib.pyplot as plt


REFERENCE_SETTINGS = {
    "font.family": "serif", "font.serif": ["DejaVu Serif"],
    "font.size": 14, "axes.labelsize": 14, "axes.titlesize": 14,
    "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 12,
    "axes.linewidth": 1.2, "axes.labelpad": 4, "axes.xmargin": .04,
    "xtick.major.size": 6, "ytick.major.size": 6,
    "xtick.minor.size": 3, "ytick.minor.size": 3,
    "xtick.major.width": 1.1, "ytick.major.width": 1.1,
    "xtick.minor.width": .9, "ytick.minor.width": .9,
    "lines.linewidth": 1.4, "lines.markersize": 6,
    "legend.frameon": True, "legend.framealpha": 1.,
    "legend.edgecolor": ".8", "legend.fancybox": False,
}


@dataclass
class FigureStyle:
    """APS base with reference-sized serif labels/ticks, 300 dpi, local rc.

    Use ``with style.context():`` around additional notebook artists or drawing
    into existing axes. ``save`` fixes export dpi independently of global rc.
    MathText supports mathsf/mathrm without TeX; usetex enables real LaTeX with
    a minimal customizable preamble. ``labels`` maps default text to raw TeX.
    """

    dpi: int = 300
    figsize: tuple | None = (6.0, 3.6)
    usetex: bool = False
    settings: dict = field(default_factory=dict)
    math_fontset: str = "cm"
    latex_preamble: str = r"\usepackage{amsmath}"
    labels: dict = field(default_factory=dict)
    shade_alpha: float = .18

    @contextmanager
    def context(self):
        try:
            from plotting_lib import update_settings
        except ModuleNotFoundError as error:
            if error.name != "plotting_lib":
                raise
            raise ImportError("Install the notebook style package: bash scripts/python.sh -m pip install "
                              "--no-deps --no-build-isolation -e external/plotting_lib") from error
        with mpl.rc_context():
            update_settings(style="aps", usetex=self.usetex,
                            latex_preamble=self.latex_preamble or " ",
                            settings={**REFERENCE_SETTINGS, "mathtext.fontset": self.math_fontset,
                                      "text.usetex": self.usetex, "figure.dpi": self.dpi,
                                      "savefig.dpi": self.dpi, **self.settings})
            yield

    def label(self, text):
        """Apply explicit label overrides; safely escape generated TeX text."""
        if text in self.labels:
            return self.labels[text]
        if not self.usetex:
            return text
        escape = {"\\": r"\textbackslash{}", "_": r"\_", "%": r"\%", "&": r"\&",
                  "$": r"\$", "#": r"\#", "{": r"\{", "}": r"\}",
                  "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
        return "".join(escape.get(c, c) for c in text)

    def axis_labels(self, ax, xlabel, ylabel):
        ax.set(xlabel=self.label(xlabel), ylabel=self.label(ylabel))

    def axes(self, ax=None):
        if ax is not None:
            return ax.figure, ax
        return plt.subplots(figsize=self.figsize, dpi=self.dpi, layout="constrained")

    def save(self, fig, path, **kwargs):
        options = {"dpi": self.dpi, "bbox_inches": "tight", **kwargs}
        with self.context():
            fig.savefig(path, **options)
