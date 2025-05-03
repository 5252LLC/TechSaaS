#!/usr/bin/env node

/**
 * Simple task viewer and manager for TechSaaS project
 * This script provides basic functionality to view and update tasks
 * without requiring the full task-master-ai package
 */

const fs = require('fs');
const path = require('path');

// Task file location
const TASKS_FILE = path.join(__dirname, 'tasks', 'tasks.json');

// Load tasks
function loadTasks() {
  try {
    const data = fs.readFileSync(TASKS_FILE, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error(`Error loading tasks: ${error.message}`);
    process.exit(1);
  }
}

// Save tasks
function saveTasks(tasksData) {
  try {
    fs.writeFileSync(TASKS_FILE, JSON.stringify(tasksData, null, 2), 'utf8');
    console.log('Tasks saved successfully.');
  } catch (error) {
    console.error(`Error saving tasks: ${error.message}`);
  }
}

// List all tasks
function listTasks() {
  const tasksData = loadTasks();
  const tasks = tasksData.tasks;
  
  console.log('\n===== TechSaaS Tasks =====\n');
  
  // Group tasks by status
  const pendingTasks = tasks.filter(t => t.status === 'pending');
  const inProgressTasks = tasks.filter(t => t.status === 'in-progress');
  const doneTasks = tasks.filter(t => t.status === 'done');
  const otherTasks = tasks.filter(t => !['pending', 'in-progress', 'done'].includes(t.status));
  
  // Display in-progress tasks
  console.log('\n== IN PROGRESS ==');
  if (inProgressTasks.length === 0) {
    console.log('No tasks in progress.');
  } else {
    inProgressTasks.forEach(t => {
      console.log(`[${t.id}] ${t.title} - Priority: ${t.priority}`);
      console.log(`    Dependencies: ${t.dependencies.join(', ') || 'None'}`);
      console.log('');
    });
  }
  
  // Display pending tasks
  console.log('\n== PENDING ==');
  if (pendingTasks.length === 0) {
    console.log('No pending tasks.');
  } else {
    pendingTasks.forEach(t => {
      console.log(`[${t.id}] ${t.title} - Priority: ${t.priority}`);
      console.log(`    Dependencies: ${t.dependencies.join(', ') || 'None'}`);
      console.log('');
    });
  }
  
  // Display done tasks count
  console.log(`\n== COMPLETED: ${doneTasks.length} tasks ==`);
  
  // Project progress
  console.log(`\nProject Progress: ${Math.round((doneTasks.length / tasks.length) * 100)}%`);
}

// Show task details
function showTask(id) {
  const tasksData = loadTasks();
  const task = tasksData.tasks.find(t => t.id === parseInt(id));
  
  if (!task) {
    console.error(`Task ID ${id} not found.`);
    return;
  }
  
  console.log('\n===== Task Details =====\n');
  console.log(`ID: ${task.id}`);
  console.log(`Title: ${task.title}`);
  console.log(`Status: ${task.status}`);
  console.log(`Priority: ${task.priority}`);
  console.log(`Dependencies: ${task.dependencies.join(', ') || 'None'}`);
  console.log('\nDescription:');
  console.log(task.description);
  console.log('\nDetails:');
  console.log(task.details);
  console.log('\nTest Strategy:');
  console.log(task.testStrategy || 'None specified');
  
  if (task.subtasks && task.subtasks.length > 0) {
    console.log('\nSubtasks:');
    task.subtasks.forEach(st => {
      console.log(`- [${st.id}] ${st.title} (${st.status})`);
    });
  }
}

// Update task status
function updateTaskStatus(id, status) {
  const validStatuses = ['pending', 'in-progress', 'done', 'deferred'];
  
  if (!validStatuses.includes(status)) {
    console.error(`Invalid status. Must be one of: ${validStatuses.join(', ')}`);
    return;
  }
  
  const tasksData = loadTasks();
  const taskIndex = tasksData.tasks.findIndex(t => t.id === parseInt(id));
  
  if (taskIndex === -1) {
    console.error(`Task ID ${id} not found.`);
    return;
  }
  
  tasksData.tasks[taskIndex].status = status;
  saveTasks(tasksData);
  console.log(`Task ${id} status updated to ${status}.`);
}

// Next tasks to work on
function nextTasks() {
  const tasksData = loadTasks();
  const tasks = tasksData.tasks;
  
  // Find tasks that are pending and have all dependencies completed
  const pendingTasks = tasks.filter(t => t.status === 'pending');
  const readyTasks = pendingTasks.filter(task => {
    if (!task.dependencies || task.dependencies.length === 0) return true;
    
    return task.dependencies.every(depId => {
      const depTask = tasks.find(t => t.id === depId);
      return depTask && depTask.status === 'done';
    });
  });
  
  // Sort by priority (high, medium, low) and then by ID
  const priorityOrder = { 'high': 0, 'medium': 1, 'low': 2 };
  readyTasks.sort((a, b) => {
    const priorityA = priorityOrder[a.priority] || 99;
    const priorityB = priorityOrder[b.priority] || 99;
    
    if (priorityA !== priorityB) return priorityA - priorityB;
    return a.id - b.id;
  });
  
  console.log('\n===== Next Tasks to Work On =====\n');
  
  if (readyTasks.length === 0) {
    console.log('No pending tasks with completed dependencies.');
    return;
  }
  
  readyTasks.slice(0, 3).forEach(task => {
    console.log(`[${task.id}] ${task.title} - Priority: ${task.priority}`);
    console.log(`    Description: ${task.description}`);
    console.log('');
  });
}

// Command line argument handling
function main() {
  const args = process.argv.slice(2);
  const command = args[0];
  
  switch (command) {
    case 'list':
      listTasks();
      break;
    case 'show':
      if (!args[1]) {
        console.error('Please provide a task ID.');
        break;
      }
      showTask(args[1]);
      break;
    case 'update':
      if (!args[1] || !args[2]) {
        console.error('Usage: node task-view.js update <task-id> <status>');
        break;
      }
      updateTaskStatus(args[1], args[2]);
      break;
    case 'next':
      nextTasks();
      break;
    default:
      console.log('TechSaaS Task Manager');
      console.log('Usage:');
      console.log('  node task-view.js list - List all tasks');
      console.log('  node task-view.js show <task-id> - Show task details');
      console.log('  node task-view.js update <task-id> <status> - Update task status');
      console.log('  node task-view.js next - Show next tasks to work on');
      break;
  }
}

main();
