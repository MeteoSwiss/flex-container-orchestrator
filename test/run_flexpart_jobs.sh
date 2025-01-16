#!/bin/bash

# Clean up the SQLite database
rm -rf ~/.sqlite/sqlite3-db

# Array of job parameters
jobs=(
  "--step 00 --date 20250119 --time 00 --location s3://flexpart-input/P1D01190000011900001"
  "--step 00 --date 20250119 --time 00 --location s3://flexpart-input/P1S01190000011900011"
  "--step 01 --date 20250119 --time 00 --location s3://flexpart-input/P1S01190000011901001"
  "--step 02 --date 20250119 --time 00 --location s3://flexpart-input/P1S01190000011902001"
  "--step 03 --date 20250119 --time 00 --location s3://flexpart-input/P1S01190000011903001"
  "--step 04 --date 20250119 --time 00 --location s3://flexpart-input/P1S01190000011904001"
  "--step 05 --date 20250119 --time 00 --location s3://flexpart-input/P1S01190000011905001"
  "--step 06 --date 20250119 --time 00 --location s3://flexpart-input/P1S01190000011906001"
  "--step 00 --date 20250118 --time 18 --location s3://flexpart-input/P1S01181800011818001"
  "--step 00 --date 20250118 --time 18 --location s3://flexpart-input/P1S01181800011818011"
  "--step 01 --date 20250118 --time 18 --location s3://flexpart-input/P1S01181800011819001"
  "--step 02 --date 20250118 --time 18 --location s3://flexpart-input/P1S01181800011820001"
  "--step 03 --date 20250118 --time 18 --location s3://flexpart-input/P1S01181800011821001"
  "--step 04 --date 20250118 --time 18 --location s3://flexpart-input/P1S01181800011822001"
  "--step 05 --date 20250118 --time 18 --location s3://flexpart-input/P1S01181800011823001"
  "--step 06 --date 20250118 --time 18 --location s3://flexpart-input/P1S01181800011900001"
)

# Execute each job
for job in "${jobs[@]}"; do
  $HOME/.local/bin/poetry run python3 flex_container_orchestrator/main.py $job
done

