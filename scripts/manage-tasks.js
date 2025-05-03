#!/usr/bin/env node

// Convert ES module imports to CommonJS require
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// Get current file directory
const __dirname = path.dirname(require.main.filename);

// Path to tasks.json
const tasksPath = path.join(__dirname, '..', 'tasks', 'tasks.json');

// Function to read tasks.json
function readTasks() {
  try {
    const data = fs.readFileSync(tasksPath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error(`Error reading tasks file: ${error.message}`);
    process.exit(1);
  }
}

// Function to write tasks.json
function writeTasks(tasks) {
  try {
    fs.writeFileSync(tasksPath, JSON.stringify(tasks, null, 2), 'utf8');
    console.log('Tasks successfully updated.');
  } catch (error) {
    console.error(`Error writing tasks file: ${error.message}`);
    process.exit(1);
  }
}

// Function to list tasks
function listTasks() {
  const tasks = readTasks();
  
  console.log('\n======== 52TechSaas Tasks ========\n');
  
  tasks.tasks.forEach(task => {
    console.log(`[Task ${task.id}] ${task.title} - ${task.status.toUpperCase()}`);
    
    if (task.subtasks && task.subtasks.length > 0) {
      task.subtasks.forEach(subtask => {
        const statusIcon = subtask.status === 'done' ? '✅' : 
                          subtask.status === 'pending' ? '⏳' : '⏸️';
        console.log(`  ${statusIcon} [${task.id}.${subtask.id}] ${subtask.title} - ${subtask.status.toUpperCase()}`);
      });
    }
    
    console.log('');
  });
}

// Function to update task status
function updateTaskStatus(taskId, subtaskId, newStatus) {
  const tasks = readTasks();
  
  if (subtaskId) {
    // Update subtask status
    const task = tasks.tasks.find(t => t.id === parseInt(taskId));
    if (!task) {
      console.error(`Task with ID ${taskId} not found.`);
      return;
    }
    
    const subtask = task.subtasks.find(s => s.id === parseInt(subtaskId));
    if (!subtask) {
      console.error(`Subtask ${subtaskId} of task ${taskId} not found.`);
      return;
    }
    
    subtask.status = newStatus;
    console.log(`Updated status of task ${taskId}.${subtaskId} to ${newStatus}.`);
  } else {
    // Update main task status
    const task = tasks.tasks.find(t => t.id === parseInt(taskId));
    if (!task) {
      console.error(`Task with ID ${taskId} not found.`);
      return;
    }
    
    task.status = newStatus;
    console.log(`Updated status of task ${taskId} to ${newStatus}.`);
  }
  
  writeTasks(tasks);
}

// Main function
function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0 || args[0] === 'list') {
    listTasks();
  } else if (args[0] === 'set-status') {
    // Check required arguments
    if (args.length < 3) {
      console.error('Usage: node manage-tasks.js set-status <taskId>[.<subtaskId>] <status>');
      process.exit(1);
    }
    
    // Parse task ID and subtask ID if provided
    const idParts = args[1].split('.');
    const taskId = idParts[0];
    const subtaskId = idParts.length > 1 ? idParts[1] : null;
    const status = args[2];
    
    // Validate status
    if (!['pending', 'done', 'deferred'].includes(status)) {
      console.error('Status must be one of: pending, done, deferred');
      process.exit(1);
    }
    
    updateTaskStatus(taskId, subtaskId, status);
  } else {
    console.error(`Unknown command: ${args[0]}`);
    console.error('Available commands: list, set-status');
    process.exit(1);
  }
}

// Run the script
main();
