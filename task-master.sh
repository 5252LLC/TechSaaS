#!/bin/bash

# TaskMaster wrapper script for 52TechSaas project
# Created: May 3, 2025
# Usage: ./task-master.sh [command] [options]
# Example: ./task-master.sh list
#          ./task-master.sh show 7.1
#          ./task-master.sh set-status --id=7.1 --status=done

TASK_MASTER_PATH="/home/fiftytwo/Desktop/52 codes/claude-task-master"
TASKS_FILE="/home/fiftytwo/Desktop/52 codes/52TechSaas/tasks/tasks.json"

# Check if command is provided
if [ $# -eq 0 ]; then
  echo "Error: Command required"
  echo "Usage: ./task-master.sh [command] [options]"
  echo "Example: ./task-master.sh list"
  exit 1
fi

# Get command and remove it from arguments
COMMAND=$1
shift

# Execute command with remaining arguments
cd "$TASK_MASTER_PATH" && node scripts/dev.js "$COMMAND" --file="$TASKS_FILE" "$@"
