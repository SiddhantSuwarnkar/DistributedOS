<div align="center">

# Distributed OS Task Manager

**A fully featured distributed operating system simulation built in Python with CustomTkinter, Socket Programming, and Matplotlib.**

CPU Scheduling · Memory Allocation · Disk Scheduling · Deadlock Handling · Distributed Workers · Live Analytics · Resource Monitoring

---

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square\&logo=python)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-green?style=flat-square)
![Networking](https://img.shields.io/badge/Networking-TCP%20Sockets-orange?style=flat-square)
![OS](https://img.shields.io/badge/Domain-Operating%20Systems-purple?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

</div>

---

## Table of Contents

* [Overview](#overview)
* [Features](#features)
* [Project Structure](#project-structure)
* [Installation](#installation)
* [How to Run](#how-to-run)
* [System Architecture](#system-architecture)
* [CPU Scheduling Algorithms](#cpu-scheduling-algorithms)
* [Memory Allocation Algorithms](#memory-allocation-algorithms)
* [Disk Scheduling Algorithms](#disk-scheduling-algorithms)
* [Deadlock Prevention and Recovery](#deadlock-prevention-and-recovery)
* [UI Modules](#ui-modules)
* [Analytics and Metrics](#analytics-and-metrics)
* [Networking Model](#networking-model)
* [Technical Design](#technical-design)
* [Academic Context](#academic-context)
* [Requirements](#requirements)

---

## Overview

Distributed OS Task Manager is a complete simulation of a distributed operating system where multiple worker nodes connect to a central coordinator over a local network.

The coordinator receives jobs, schedules processes, allocates resources, handles deadlocks, monitors workers, and visualizes system performance in real time.

The project was built as an academic implementation of core Operating System concepts combined into one practical system using networking and GUI programming.

---

## Features

### Core System

* Multi client distributed architecture
* Central coordinator server with control dashboard
* Worker nodes connected over TCP sockets
* Real time task dispatch and execution
* Live connected device monitoring
* Multi tab interactive desktop UI

### Operating System Modules

* CPU Scheduling
* Memory Allocation
* Disk Scheduling
* Deadlock Detection
* Deadlock Recovery
* Resource Allocation
* Throughput Measurement
* Waiting Time Calculation
* Turnaround Time Calculation
* CPU Utilization Tracking

### Visualization

* Process queue panels
* Running and completed task lists
* Banker live table
* Deadlock logs
* Resource cards for workers
* Gantt chart
* Performance metrics dashboard

### Communication

* Group chat between coordinator and workers
* Session tracking
* Real time JSON message exchange

---

## Project Structure

```text
DistributedOS/
│
├── coordinator.py         # Main coordinator server, GUI, scheduler, analytics
├── client.py              # Worker node client application
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
└── assets/                # Optional resources
```

### Module Responsibilities

| File               | Responsibility                                                                   |
| ------------------ | -------------------------------------------------------------------------------- |
| `coordinator.py`   | Central server, scheduling engine, deadlock manager, analytics dashboard         |
| `client.py`        | Connects to coordinator, receives jobs, executes tasks, sends completion updates |
| `requirements.txt` | Stores required Python packages                                                  |
| `README.md`        | Documentation                                                                    |

---

## Installation

**Prerequisites:** Python 3.9 or higher.

```bash
# 1. Clone the repository
git clone https://github.com/SiddhantSuwarnkar/DistributedOS.git
cd DistributedOS

# 2. Create virtual environment
python -m venv venv

# 3. Activate environment
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux / macOS

# 4. Install dependencies
pip install -r requirements.txt
```

---

## How to Run

### Start Coordinator

```bash
python coordinator.py
```

This starts the main dashboard and server.

### Start Worker Nodes

Open new terminals or run on other systems:

```bash
python client.py
```

Each worker connects to the coordinator and becomes available for task execution.

---

## System Architecture

```text
+------------------------+
|      Coordinator       |
| Scheduler              |
| Deadlock Manager       |
| Analytics Dashboard    |
+-----------+------------+
            |
       TCP Socket Network
            |
--------------------------------
|              |               |
Worker 1     Worker 2       Worker 3
```

### Coordinator Responsibilities

* Accept worker connections
* Maintain ready queue
* Select scheduling algorithm
* Allocate resources
* Detect deadlocks
* Recover system state
* Update UI and metrics

### Worker Responsibilities

* Join network
* Receive tasks
* Simulate execution
* Return completion status
* Share live usage state

---

## CPU Scheduling Algorithms

The coordinator supports multiple scheduling policies.

### FCFS

First Come First Serve executes in arrival order.

### SJF

Shortest Job First selects smallest burst time first.

### Priority Scheduling

Higher priority jobs run before lower priority jobs.

### Round Robin

Processes rotate fairly through the queue.

### Concepts Demonstrated

* Fairness
* Starvation
* Response time
* Average waiting time
* Turnaround time

---

## Memory Allocation Algorithms

The system supports common memory allocation methods.

### First Fit

Allocates first available block that is large enough.

### Best Fit

Allocates smallest suitable block.

### Worst Fit

Allocates largest available block.

### Next Fit

Search continues from previous allocation point.

### Concepts Demonstrated

* Internal fragmentation
* External fragmentation
* Search efficiency
* Allocation strategy tradeoffs

---

## Disk Scheduling Algorithms

The project simulates disk request servicing algorithms.

### FCFS

Requests served in arrival order.

### SSTF

Shortest Seek Time First chooses nearest request.

### SCAN

Head moves in one direction servicing requests, then reverses.

### C SCAN

Head moves in one direction and jumps back to start.

### Concepts Demonstrated

* Seek time reduction
* Head movement optimization
* Throughput tradeoffs
* Starvation possibility

---

## Deadlock Prevention and Recovery

The system includes live deadlock simulation and recovery.

### Banker Based Prediction

Before granting resources, the system checks whether the request keeps the state safe.

### Deadlock Detection

Blocked processes are monitored continuously.

### Recovery Strategy

* Abort one victim process
* Release allocated resources
* Requeue remaining blocked processes
* Resume normal scheduling

### Visualization

Deadlock tab displays:

* Banker live table
* Process state
* Max resources
* Allocation
* Need
* Decision logs
* Recovery history
* SAFE or DEADLOCK indicator

---

## UI Modules

### Control Tab

* Queue list
* Running tasks
* Completed tasks
* Sessions
* Algorithm selectors

### Devices Tab

* Connected workers
* CPU usage
* RAM usage
* Disk usage
* Worker state cards

### Analytics Tab

* Average waiting time
* Average turnaround time
* Throughput
* CPU utilization
* Gantt chart
* Task history

### Chat Tab

* Group communication
* Broadcast messages
* Worker chat

### Deadlock Tab

* Banker table
* Detection logs
* Recovery actions
* Resource availability

---

## Analytics and Metrics

The coordinator calculates live system metrics.

### Average Waiting Time

Time spent in queue before execution.

### Average Turnaround Time

Total time from arrival to completion.

### Throughput

Completed tasks per second.

### CPU Utilization

Average CPU load of workers.

### Gantt Chart

Timeline of recently completed tasks.

---

## Networking Model

### Communication Stack

* TCP sockets
* JSON packets
* Multi threaded server
* Multi client connections

### Message Types

* join
* task_request
* run_task
* task_done
* chat
* session_start
* session_stop

### Benefits

* Real distributed communication
* Expandable architecture
* Practical client server model

---

## Technical Design

### GUI Framework

Built using CustomTkinter and Tkinter widgets for a modern desktop interface.

### Concurrency

Uses Python threads for:

* Accepting clients
* Scheduler loop
* Deadlock monitor
* UI updates

### Visualization Layer

Uses Matplotlib for charts and live Gantt graph rendering.

### Data Handling

Uses Python dictionaries, queues, lists, and JSON packets for state management.

---

## Academic Context

This project was developed as an Operating Systems academic project covering multiple major topics in one implementation.

### Concepts Covered

* Process Scheduling
* Deadlocks
* Resource Allocation
* Memory Management
* Disk Scheduling
* Distributed Systems
* Networking
* Concurrency
* Performance Metrics
* GUI Based Simulation

### Suitable For

* OS Mini Project
* Semester Project
* Lab Demonstration
* Viva Presentation
* Academic Submission

---

## Requirements

Create a file named `requirements.txt` with:

```text
customtkinter
matplotlib
```

Then install:

```bash
pip install -r requirements.txt
```

### Python Version

```text
Python >= 3.9
```

---

<div align="center">

Built with Python · Operating Systems · Networking · Scheduling · Academic Project

</div>
