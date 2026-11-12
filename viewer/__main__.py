"""Entry point: ``python -m viewer``."""

from viewer.app import _parse_args, run_viewer

if __name__ == "__main__":
    args = _parse_args()
    run_viewer(
        window_type="offscreen" if args.offscreen else "onscreen",
        auto_quit_after=args.seconds,
        agent_name=args.agent,
        seed=args.seed,
    )
