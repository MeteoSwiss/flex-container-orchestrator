import logging
import os
from pathlib import Path
import subprocess
import sys

from flex_container_orchestrator.domain.lead_time_aggregator import run_aggregator
from flex_container_orchestrator import CONFIG
from dotenv import load_dotenv

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

def login_ecr():
    """
    Log in to AWS ECR by retrieving the login password and passing it to Docker login.
    """

    load_dotenv(dotenv_path=Path(".env"),)
    load_dotenv(dotenv_path=Path(".env.secrets"))

    region = os.getenv("AWS_REGION", "eu-central-2")
    AWS_ACCOUNT_ID=os.getenv('AWS_ACCOUNT_ID')
    if not AWS_ACCOUNT_ID:
        raise ValueError("AWS_ACCOUNT_ID environment variable is not set")

    repo_url=f"{AWS_ACCOUNT_ID}.dkr.ecr.{region}.amazonaws.com"
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

def main(date: str, location: str, time: str, step: str) -> None:
    # Retrieve ECR login password and log in to Docker
    login_ecr()

    # Set only what you know so far
    env_vars = {
        "DATE": date,
        "TIME": time,
        "STEP": step,
        "LOCATION": location,
        "MAIN__DB_PATH": CONFIG.main.db.path,

        # Placeholders for later-use vars to suppress warnings
        "RELEASE_SITE_NAME": "",
        "IBDATE": "",
        "IBTIME": "",
        "IEDATE": "",
        "IETIME": "",
        "FORECAST_DATETIME": "",
        "PRESET": ""
    }

    # Write to .env
    with open(".env", "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    # ====== Run flexprep ======
    try:
        # Run Docker Compose to launch flexprep
        docker_compose_command = ["docker", "compose", "run", "--rm", "flexprep"]
        run_command(docker_compose_command)

    except subprocess.CalledProcessError:
        logger.error("Flexprep failed.")
        sys.exit(1)

    logger.info("Pre-processing container executed successfully.")

    # ====== Run lead_time_aggregator.py ======
    try:
        configurations = run_aggregator(date, time, int(step))

    except Exception as e:
        logger.error("Aggregator encountered an error: %s", e)
        sys.exit(1)

    logger.info("Aggregator launch script executed successfully.")

    # ====== Run Flexpart and Pyflexplot ======
    for config in configurations:
        env_vars.update({
            "RELEASE_SITE_NAME": "BEZ",
            "IBDATE": config["IBDATE"],
            "IBTIME": config["IBTIME"],
            "IEDATE": config["IEDATE"],
            "IETIME": config["IETIME"],
            "FORECAST_DATETIME": config["FORECAST_DATETIME"],
            "PRESET": "opr/ifs-hres-eu/all_pdf"
        })

        with open(".env", "w") as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

        try:
            # Launch Flexpart using Docker Compose
            docker_compose_command = ["docker", "compose", "run", "--rm", "flexpart"]
            run_command(docker_compose_command)

        except subprocess.CalledProcessError:
            logger.error("Error running Flexpart for configuration: %s", config)
            sys.exit(1)

        try:
            # Launch Pyflexplot using Docker Compose
            docker_compose_command = ["docker", "compose", "run", "--rm", "pyflexplot"]
            run_command(docker_compose_command)

        except subprocess.CalledProcessError:
            logger.error("Error running Pyflexplot for configuration: %s", config)
            sys.exit(1)
