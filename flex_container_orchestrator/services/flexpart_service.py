import json
import logging
import os
import subprocess
import sys


def run_command(command: list[str] | str, capture_output: bool = False) -> bytes | None:
    """
    Helper function to run shell commands and handle errors.
    """
    try:
        if capture_output:
            return subprocess.check_output(command).strip()
        subprocess.check_call(command)
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{' '.join(command)}' failed with error: {e}")
        sys.exit(1)

    return None


def launch_containers(date: str, location: str, time: str, step: str) -> None:
    logging.basicConfig(level=logging.INFO)

    # Retrieve ECR login password and log in to Docker
    try:
        login_command = ["aws", "ecr", "get-login-password", "--region", "eu-central-2"]
        login_password = run_command(login_command, capture_output=True)

        docker_login_command = [
            "docker",
            "login",
            "--username",
            "AWS",
            "--password-stdin",
            "493666016161.dkr.ecr.eu-central-2.amazonaws.com",
        ]

        process = subprocess.Popen(docker_login_command, stdin=subprocess.PIPE)
        process.communicate(input=login_password)

        if process.returncode != 0:
            logging.error("Docker login failed. Exiting.")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        logging.error("Error logging in to Docker: %s", e)
        sys.exit(1)

    # ====== First part: Run pre-processing for Flexpart ======
    db_mount = os.path.expanduser(f"{os.getenv('DB_MOUNT')}")
    docker_image = f"{os.getenv('ECR_REPO')}:{os.getenv('TAG')}"
    env_file_path = os.path.expanduser(
        "~/flex-container-orchestrator/flex_container_orchestrator/config/.env"
    )

    if not os.path.exists(db_mount):
        logging.error("SQLite database directory %s does not exist.", db_mount)
        sys.exit(1)

    try:
        docker_run_command = [
            "docker",
            "run",
            "--rm",
            "--mount",
            f"type=bind,source={db_mount},destination=/src/db/",
            "--env-file",
            env_file_path,
            docker_image,
            "--step",
            step,
            "--date",
            date,
            "--time",
            time,
            "--location",
            location,
        ]
        run_command(docker_run_command)  # type: ignore

    except subprocess.CalledProcessError:
        logging.error("Docker run processing failed.")
        sys.exit(1)

    logging.info("Pre-processing container executed successfully.")

    # ====== Second part: Run aggregator_flexpart.py ======
    db_path = os.path.join(db_mount, "sqlite3-db")

    if not os.path.exists(db_path):
        logging.error("Database file %s does not exist.", db_path)
        sys.exit(1)

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        aggregator_script_path = os.path.join(
            script_dir, "..", "domain", "aggregator_flexpart.py"
        )

        aggregator_command = [
            "python3",
            aggregator_script_path,
            "--date",
            date,
            "--time",
            time,
            "--step",
            step,
            "--db_path",
            db_path,
        ]

        output = run_command(aggregator_command, capture_output=True)
        if not output:
            logging.info(
                "Flexpart can't be launched. Not enough pre-processed files. Exiting."
            )
            sys.exit(0)
        try:
            configurations = json.loads(output.decode("utf-8"))
        except json.JSONDecodeError as e:
            logging.error("JSON decode error: %s", e)
            sys.exit(1)

    except subprocess.CalledProcessError:
        logging.error("Aggregator script encountered an error.")
        sys.exit(1)

    logging.info("Aggregator launch script executed successfully.")

    # ====== Third part: Run Flexpart ======
    try:
        # Check if configurations is an empty list
        if not configurations:
            logging.error("Not enough data to launch Flexpart.")
            sys.exit(1)

        # Loop through each configuration and execute Flexpart
        for config in configurations:
            env_vars = [f"-e {key}={value}" for key, value in config.items()]
            command = ["/bin/sh", "-c", "ulimit -a && bash entrypoint.sh"]
            command_str = " ".join(command)

            docker_command = (
                f"docker run --env-file {env_file_path}  {' '.join(env_vars)} --rm  "
                "container-registry.meteoswiss.ch/flexpart-poc/flexpart:containerize "
                f"{command_str}"
            )

            logging.info("Running: %s", docker_command)
            run_command(docker_command)

    except subprocess.CalledProcessError:
        logging.error("Launch Flexpart script encountered an error.")
        sys.exit(1)

    logging.info("Launch Flexpart script executed successfully.")
