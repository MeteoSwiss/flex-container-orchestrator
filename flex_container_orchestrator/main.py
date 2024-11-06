import argparse
import logging

from flex_container_orchestrator.services import flexpart_service

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="Date parameter in format YYYYMMDD"
    )

    parser.add_argument(
        "--location",
        type=str,
        required=True,
        help="Location parameter"
    )

    parser.add_argument(
        "--time",
        type=str,
        required=True,
        help="Time parameter in format HH"
    )

    parser.add_argument(
        "--step",
        type=str,
        required=True,
        help="Step parameter"
    )
    args = parser.parse_args()

    flexpart_service.launch_containers(args.date, args.location, args.time, args.step)


if __name__ == "__main__":
    main()
