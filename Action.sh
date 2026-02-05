echo "Running BMS Final Check"
cd /home/main/Documents/BMS/ || exit 1  # Exit if the directory change fails
pwd
source venv/bin/activate || exit 1  # Exit if activation fails
cd /home/main/Documents/BMS_Final_Check || exit 1  # Exit if the directory change fails
pwd

# TO RUN THE BMS FINAL CHECK
# python3 BMS_Final_Check.py

# TO RUN THE BASH SCRIPT
# source Action.sh
