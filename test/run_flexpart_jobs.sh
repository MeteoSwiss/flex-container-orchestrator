#!/bin/bash

# This script tests the full workflow from preprocessing to FLEXPART and PyFlexPlot.
# It includes the necessary input data to execute a single FLEXPART run.
# The user needs to adjust the date and time of the forecast files
# to ensure that the forecast is available in the S3 bucket (from the last three days).

# Clean up the SQLite database
rm -rf ~/.sqlite/sqlite3-db

# Get today's date and compute dates for the last three days
TODAY=$(date -u +"%Y%m%d")
YESTERDAY=$(date -u -d "yesterday" +"%Y%m%d")

# Array of job parameters with dynamic date handling
jobs=(
  "--step 00 --date $TODAY --time 00 --location s3://flexpart-input/P1D${TODAY}0000${TODAY}00001"
  "--step 00 --date $TODAY --time 00 --location s3://flexpart-input/P1S${TODAY}0000${TODAY}00011"
  "--step 01 --date $TODAY --time 00 --location s3://flexpart-input/P1S${TODAY}0000${TODAY}01001"
  "--step 02 --date $TODAY --time 00 --location s3://flexpart-input/P1S${TODAY}0000${TODAY}02001"
  "--step 03 --date $TODAY --time 00 --location s3://flexpart-input/P1S${TODAY}0000${TODAY}03001"
  "--step 04 --date $TODAY --time 00 --location s3://flexpart-input/P1S${TODAY}0000${TODAY}04001"
  "--step 05 --date $TODAY --time 00 --location s3://flexpart-input/P1S${TODAY}0000${TODAY}05001"
  "--step 06 --date $TODAY --time 00 --location s3://flexpart-input/P1S${TODAY}0000${TODAY}06001"
  "--step 00 --date $YESTERDAY --time 18 --location s3://flexpart-input/P1S${YESTERDAY}1800${YESTERDAY}18001"
  "--step 00 --date $YESTERDAY --time 18 --location s3://flexpart-input/P1S${YESTERDAY}1800${YESTERDAY}18011"
  "--step 01 --date $YESTERDAY --time 18 --location s3://flexpart-input/P1S${YESTERDAY}1800${YESTERDAY}19001"
  "--step 02 --date $YESTERDAY --time 18 --location s3://flexpart-input/P1S${YESTERDAY}1800${YESTERDAY}20001"
  "--step 03 --date $YESTERDAY --time 18 --location s3://flexpart-input/P1S${YESTERDAY}1800${YESTERDAY}21001"
  "--step 04 --date $YESTERDAY --time 18 --location s3://flexpart-input/P1S${YESTERDAY}1800${YESTERDAY}22001"
  "--step 05 --date $YESTERDAY --time 18 --location s3://flexpart-input/P1S${YESTERDAY}1800${YESTERDAY}23001"
  "--step 06 --date $YESTERDAY --time 18 --location s3://flexpart-input/P1S${YESTERDAY}1800${TODAY}00001"
)

# Execute each job
for job in "${jobs[@]}"; do
  $HOME/.local/bin/poetry run python3 flex_container_orchestrator/main.py $job
done
