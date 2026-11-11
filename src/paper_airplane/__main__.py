"""Command line entry: python -m paper_airplane."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Paper Airplane Flight Lab.")
    parser.add_argument(
        "--reference-plots",
        action="store_true",
        help="Write Figure 1 and Figure 2 for cases a-d.",
    )
    parser.add_argument(
        "--heatmap",
        action="store_true",
        help="Write the physical landing-range heatmap.",
    )
    args = parser.parse_args(argv)
    if not args.reference_plots and not args.heatmap:
        print(
            "Paper Airplane Flight Lab skeleton is installed. "
            "The flight window is added in a later milestone."
        )
        return 0

    import matplotlib

    matplotlib.use("Agg", force=True)
    from paper_airplane.plots import write_heatmap, write_reference_plots

    if args.reference_plots:
        print(write_reference_plots())
    if args.heatmap:
        print(write_heatmap())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
