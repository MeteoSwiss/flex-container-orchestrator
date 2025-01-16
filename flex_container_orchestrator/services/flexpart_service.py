import logging
import os
import subprocess
import sys

from flex_container_orchestrator.domain.lead_time_aggregator import run_aggregator
from flex_container_orchestrator import CONFIG


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
        login_command = ["aws", "ecr", "get-login-password", "--region", region, "--profile", "ecr-readonly"]
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

    # Set environment variables required by Docker Compose
    os.environ["DATE"] = date
    os.environ["LOCATION"] = location
    os.environ["TIME"] = time
    os.environ["STEP"] = step
    os.environ["MAIN__DB_PATH"] = CONFIG.main.db.path

    try:
        # Run Docker Compose to launch services
        docker_compose_command = ["docker", "compose", "run", "--rm", "flexprep"]
        run_command(docker_compose_command)

    except subprocess.CalledProcessError:
        logger.error("Docker Compose run failed.")
        sys.exit(1)

    logger.info("Pre-processing container executed successfully.")

    # ====== Second part: Run lead_time_aggregator.py ======

    try:
        configurations = run_aggregator(date, time, int(step))

    except Exception as e:
        logger.error("Aggregator encountered an error: %s", e)
        sys.exit(1)

    logger.info("Aggregator launch script executed successfully.")

    # ====== Third part: Run Flexpart and Pyflexplot ======
    for config in configurations:
        # Set environment variables for the current configuration
        os.environ["IBDATE"] = config["IBDATE"]
        os.environ["IBTIME"] = config["IBTIME"]
        os.environ["IEDATE"] = config["IEDATE"]
        os.environ["IETIME"] = config["IETIME"]
        os.environ["RELEASE_SITE_NAME"] = "BEZ"
        os.environ["FORECAST_DATETIME"] = config["FORECAST_DATETIME"]
        os.environ["PRESET"]  = "opr/ifs-hres-eu/all_pdf"

        try:
            # Launch Flexpart using Docker Compose
            docker_compose_command = ["docker", "compose", "run", "--rm", "flexpart"]
            run_command(docker_compose_command)

        except subprocess.CalledProcessError:
            logger.error("Error running Docker Compose for configuration: %s", config)
            sys.exit(1)

        try:
            # Launch Pyflexplot using Docker Compose
            docker_compose_command = ["docker", "compose", "run", "--rm", "pyflexplot"]
            run_command(docker_compose_command)

        except subprocess.CalledProcessError:
            logger.error("Error running Docker Compose for configuration: %s", config)
            sys.exit(1)
