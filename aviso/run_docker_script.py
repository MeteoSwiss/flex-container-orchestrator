import subprocess
import argparse
import os
import sys

def main():
    # Retrieve ECR login password and log in to Docker
    try:
        login_command = [
            "aws", "ecr", "get-login-password", "--region", "eu-central-2"
        ]
        login_password = subprocess.check_output(login_command).strip()
        
        docker_login_command = [
            "docker", "login", "--username", "AWS", "--password-stdin", "493666016161.dkr.ecr.eu-central-2.amazonaws.com"
        ]
        process = subprocess.Popen(docker_login_command, stdin=subprocess.PIPE)
        process.communicate(input=login_password)
        
        if process.returncode != 0:
            print("Docker login failed. Exiting.")
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error logging in to Docker: {e}")
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

    print(f"Notification received for file {location}, date {date}, time {time}, step {step}")

    # Run pre-processing for Flexpart
    docker_image = "493666016161.dkr.ecr.eu-central-2.amazonaws.com/numericalweatherpredictions/flexpart_ifs/flexprep:2409.ee22f6c67c86b9f85185edb02924e6ab523fa0bc"

    try:
        docker_run_command = [
            "docker", "run",
            "--mount", f"type=bind,source={os.path.expanduser('~/.sqlite/')},destination=/src/db/",
            "--env-file", ".env",
            docker_image,
            "--step", step,
            "--date", date,
            "--time", time,
            "--location", location
        ]
        
        subprocess.check_call(docker_run_command)
    except subprocess.CalledProcessError:
        print("Docker run processing failed.")
        sys.exit(1)

    print("Docker container processing executed successfully.")

    # ====== Second part: Run aggregator_flexpart.py ======
    db_path = os.path.expanduser('~/.sqlite/sqlite3-db')

    try:
        aggregator_command = [
            "python3", "aggregator/aggregator_flexpart.py",
            "--date", date,
            "--time", time,
            "--step", step,
            "--db_path", db_path
        ]
        
        subprocess.check_call(aggregator_command)
    except subprocess.CalledProcessError:
        print("Aggregator launch script encountered an error.")
        sys.exit(1)

    print("Aggregator launch script executed successfully.")

    # ====== Third part: Run launch_flexpart.py ======
    try:
        launch_command = [
            "python3", "launch_flexpart.py",
            "--date", date,
            "--time", time,
            "--step", step,
            "--db_path", db_path
        ]
        
        subprocess.check_call(launch_command)
    except subprocess.CalledProcessError:
        print("Launch Flexpart script encountered an error.")
        sys.exit(1)

    print("Launch Flexpart script executed successfully.")

if __name__ == "__main__":
    main()
