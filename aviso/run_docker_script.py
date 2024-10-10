import subprocess
import argparse
import json
import os
import sys
import logging

def run_command(command, capture_output=False):
    """
    Helper function to run shell commands and handle errors.
    """
    try:
        if capture_output:
            return subprocess.check_output(command).strip()
        else:
            subprocess.check_call(command)
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{' '.join(command)}' failed with error: {e}")
        sys.exit(1)

def main():
    logging.basicConfig(level=logging.INFO)

    # Retrieve ECR login password and log in to Docker
    try:
        login_command = ["aws", "ecr", "get-login-password", "--region", "eu-central-2"]
        login_password = run_command(login_command, capture_output=True)

        docker_login_command = [
            "docker", "login", "--username", "AWS", "--password-stdin", 
            "493666016161.dkr.ecr.eu-central-2.amazonaws.com"
        ]

        process = subprocess.Popen(docker_login_command, stdin=subprocess.PIPE)
        process.communicate(input=login_password)

        if process.returncode != 0:
            logging.error("Docker login failed. Exiting.")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        logging.error(f"Error logging in to Docker: {e}")
        sys.exit(1)

    # Argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True, help='Date parameter')
    parser.add_argument('--location', required=True, help='Location parameter')
    parser.add_argument('--time', required=True, help='Time parameter')
    parser.add_argument('--step', required=True, help='Step parameter')

    args = parser.parse_args()

    date = args.date
    location = args.location
    time = args.time
    step = args.step

    logging.info(f"Notification received for file {location}, date {date}, time {time}, step {step}")

    # Run pre-processing for Flexpart
    docker_image = "493666016161.dkr.ecr.eu-central-2.amazonaws.com/numericalweatherpredictions/flexpart_ifs/flexprep:2409.ee22f6c67c86b9f85185edb02924e6ab523fa0bc"
    db_mount = os.path.expanduser('~/.sqlite/')

    if not os.path.exists(db_mount):
        logging.error(f"SQLite database directory {db_mount} does not exist.")
        sys.exit(1)

    try:
        docker_run_command = [
            "docker", "run",
            "--mount", f"type=bind,source={db_mount},destination=/src/db/",
            "--env-file", ".env",
            docker_image,
            "--step", step,
            "--date", date,
            "--time", time,
            "--location", location
        ]
        
        run_command(docker_run_command)

    except subprocess.CalledProcessError:
        logging.error("Docker run processing failed.")
        sys.exit(1)

    logging.info("Docker container processing executed successfully.")

    # ====== Second part: Run aggregator_flexpart.py ======
    db_path = os.path.expanduser('~/.sqlite/sqlite3-db')

    if not os.path.exists(db_path):
        logging.error(f"Database file {db_path} does not exist.")
        sys.exit(1)

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        aggregator_script_path = os.path.join(script_dir, '..', 'aggregator', 'aggregator_flexpart.py')

        aggregator_command = [
            "python3", aggregator_script_path,
            "--date", date,
            "--time", time,
            "--step", step,
            "--db_path", db_path
        ]

        output = run_command(aggregator_command, capture_output=True)
        try:
            configurations = json.loads(output.decode('utf-8'))
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
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
            command = ['/bin/sh', '-c', 'ulimit -a && bash entrypoint.sh']
            command_str = ' '.join(command)

            docker_command = (
                f"docker run {' '.join(env_vars)} --rm "
                "container-registry.meteoswiss.ch/flexpart-poc/flexpart:containerize "
                f"{command_str}"
            )

            logging.info(f"Running: {docker_command}")
            run_command(docker_command)

    except subprocess.CalledProcessError:
        logging.error("Launch Flexpart script encountered an error.")
        sys.exit(1)

    logging.info("Launch Flexpart script executed successfully.")


if __name__ == "__main__":
    main()
