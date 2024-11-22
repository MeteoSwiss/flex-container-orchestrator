import logging
import os
import subprocess
import sys

from flex_container_orchestrator.domain.lead_time_aggregator import run_aggregator

logger = logging.getLogger(__name__)

def run_command(command: list[str] | str, capture_output: bool = False) -> bytes | None:
    """
    Helper function to run shell commands and handle errors.
    """
    try:
        if capture_output:
            return subprocess.check_output(command).strip()
        subprocess.check_call(command)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command '{' '.join(command)}' failed with error: {e}")
        sys.exit(1)

    return None

def login_ecr(region="eu-central-2", repo_url="493666016161.dkr.ecr.eu-central-2.amazonaws.com"):
    """
    Log in to AWS ECR by retrieving the login password and passing it to Docker login.
    """
    try:
        # Step 1: Get the ECR login password
        login_command = ["aws", "ecr", "get-login-password", "--region", region]
        login_password = run_command(login_command, capture_output=True)

        # Step 2: Log in to Docker using the password
        docker_login_command = [
            "docker",
            "login",
            "--username",
            "AWS",
            "--password-stdin",
            repo_url,
        ]

        process = subprocess.Popen(docker_login_command, stdin=subprocess.PIPE)
        process.communicate(input=login_password)

        if process.returncode != 0:
            logger.error("Docker login failed. Exiting.")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        logger.error("Error logging in to Docker: %s", e)
        sys.exit(1)

def launch_containers(date: str, location: str, time: str, step: str) -> None:
    # Retrieve ECR login password and log in to Docker
    login_ecr()

    # ====== First part: Run pre-processing for Flexpart ======
    db_mount = os.path.expanduser(f"{os.getenv('DB_MOUNT')}")
    docker_image = f"{os.getenv('FLEXPREP_ECR_REPO')}:{os.getenv('FLEXPREP_TAG')}"
    env_file_path = os.path.expanduser(
        "~/flex-container-orchestrator/flex_container_orchestrator/config/.env"
    )

    if not os.path.exists(db_mount):
        logger.error("SQLite database directory %s does not exist.", db_mount)
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
        logger.error("Docker run processing failed.")
        sys.exit(1)

    logger.info("Pre-processing container executed successfully.")

    # ====== Second part: Run lead_time_aggregator.py ======
    db_path = os.path.join(db_mount, "sqlite3-db")

    if not os.path.exists(db_path):
        logger.error("Database file %s does not exist.", db_path)
        sys.exit(1)

    try:
        configurations = run_aggregator(date, time, int(step), db_path)

    except Exception as e:
        logger.error("Aggregator encountered an error: %s", e)
        sys.exit(1)

    logger.info("Aggregator launch script executed successfully.")

    # ====== Third part: Run Flexpart and Pyflexplot ======
    try:
        flexpart_image = f"{os.getenv('FLEXPART_ECR_REPO')}:{os.getenv('FLEXPART_TAG')}"
        pyflexplot_image = f"{os.getenv('PYFLEXPLOT_ECR_REPO')}:{os.getenv('PYFLEXPLOT_TAG')}"

        # Loop through each configuration and execute Flexpart
        for config in configurations:
            env_vars = [["-e", f"{key.strip()}={value}"] for key, value in config.items()]

            # Docker command for Flexpart as a list
            docker_command_flexpart = [
                "docker", "run",
                "--env-file", env_file_path,
                *[item for sublist in env_vars for item in sublist],
                "--rm",
                flexpart_image,
            ]

            logger.info("Running: %s", " ".join(docker_command_flexpart))
            run_command(docker_command_flexpart)

            s3_dest_bucket = os.environ.get("MAIN__AWS__S3__OUTPUT__NAME", "pyflexplot-output")
            s3_input_bucket = os.environ.get("MAIN__AWS__S3__INPUT__NAME", "flexpart-output")

            # Docker command for Pyflexplot as a list
            docker_command_pyflexplot = [
                "docker", "run",
                "--env-file", env_file_path,
                "--rm",
                pyflexplot_image,
                "--preset", os.environ.get("preset", ""),
                "--merge-pdfs",
                f"--dest=s3://{s3_dest_bucket}",
                "--setup", "infile",
                f"s3://{s3_input_bucket}/{config['IBDATE']}{config['IBTIME']}/sandbox/grid_conc_{config['IBDATE']}{config['IBTIME']}0000.nc",
                "--setup", "base_time", f"{config['IBDATE']}{config['IBTIME']}"
            ]

            logger.info("Running: %s", " ".join(docker_command_pyflexplot))
            run_command(docker_command_pyflexplot)

    except subprocess.CalledProcessError:
        logger.error("Launch Flexpart and Pyflexplot encountered an error.")
        sys.exit(1)
