#!/bin/bash

# This script tests the full workflow from preprocessing to FLEXPART and PyFlexPlot.
# It includes the necessary input data to execute a single FLEXPART run.
# The user needs to adjust the date and time of the forecast files
# to ensure that the forecast is available in the S3 bucket (from the last three days).

# Clean up the SQLite database
rm -rf ~/.sqlite/sqlite3-db

# Get today's date in full and short year formats
TODAY_FULL=$(date -u +"%Y%m%d")   # e.g. 20250627
TODAY_SHORT=$(date -u +"%m%d") # e.g. 0627

# Get yesterday's date in full and short year formats
YESTERDAY_FULL=$(date -u -d "yesterday" +"%Y%m%d")
YESTERDAY_SHORT=$(date -u -d "yesterday" +"%m%d")

# Array of job parameters
jobs=(
  "--step 00 --date $TODAY_FULL --time 00 --location s3://flexpart-input/P1D${TODAY_SHORT}0000${TODAY_SHORT}00001"
  "--step 00 --date $TODAY_FULL --time 00 --location s3://flexpart-input/P1S${TODAY_SHORT}0000${TODAY_SHORT}00011"
  "--step 01 --date $TODAY_FULL --time 00 --location s3://flexpart-input/P1S${TODAY_SHORT}0000${TODAY_SHORT}01001"
  "--step 02 --date $TODAY_FULL --time 00 --location s3://flexpart-input/P1S${TODAY_SHORT}0000${TODAY_SHORT}02001"
  "--step 03 --date $TODAY_FULL --time 00 --location s3://flexpart-input/P1S${TODAY_SHORT}0000${TODAY_SHORT}03001"
  "--step 04 --date $TODAY_FULL --time 00 --location s3://flexpart-input/P1S${TODAY_SHORT}0000${TODAY_SHORT}04001"
  "--step 05 --date $TODAY_FULL --time 00 --location s3://flexpart-input/P1S${TODAY_SHORT}0000${TODAY_SHORT}05001"
  "--step 06 --date $TODAY_FULL --time 00 --location s3://flexpart-input/P1S${TODAY_SHORT}0000${TODAY_SHORT}06001"
  "--step 00 --date $YESTERDAY_FULL --time 18 --location s3://flexpart-input/P1S${YESTERDAY_SHORT}1800${YESTERDAY_SHORT}18001"
  "--step 00 --date $YESTERDAY_FULL --time 18 --location s3://flexpart-input/P1S${YESTERDAY_SHORT}1800${YESTERDAY_SHORT}18011"
  "--step 01 --date $YESTERDAY_FULL --time 18 --location s3://flexpart-input/P1S${YESTERDAY_SHORT}1800${YESTERDAY_SHORT}19001"
  "--step 02 --date $YESTERDAY_FULL --time 18 --location s3://flexpart-input/P1S${YESTERDAY_SHORT}1800${YESTERDAY_SHORT}20001"
  "--step 03 --date $YESTERDAY_FULL --time 18 --location s3://flexpart-input/P1S${YESTERDAY_SHORT}1800${YESTERDAY_SHORT}21001"
  "--step 04 --date $YESTERDAY_FULL --time 18 --location s3://flexpart-input/P1S${YESTERDAY_SHORT}1800${YESTERDAY_SHORT}22001"
  "--step 05 --date $YESTERDAY_FULL --time 18 --location s3://flexpart-input/P1S${YESTERDAY_SHORT}1800${YESTERDAY_SHORT}23001"
  "--step 06 --date $YESTERDAY_FULL --time 18 --location s3://flexpart-input/P1S${YESTERDAY_SHORT}1800${TODAY_SHORT}00001"
)

# Execute each job
for job in "${jobs[@]}"; do
  $HOME/.local/bin/poetry run python3 flex_container_orchestrator/main.py $job
done
