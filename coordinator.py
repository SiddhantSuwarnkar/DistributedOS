import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import socket
import threading
import json
import subprocess
import time
import random
from collections import deque
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import os

PORT = 5000

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class CoordinatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed OS Task Manager")
        self.root.geometry("1500x920")

        self.clients = []
        self.pending_tasks = []
        self.running_tasks = []
        self.completed_tasks = []
        self.sessions = []
        self.chat_history = []

        self.completed = 0
        self.total_wait = 0
        self.total_tat = 0
        self.start_clock = time.time()

        self.gantt = deque(maxlen=12)
        self.rr_index = 0
        self.next_fit_pos = 0  # persisted across calls for NextFit memory algo

        self.lock = threading.Lock()

        self.deadlock_auto = True
        self.deadlock_mode = False

        self.proc_counter = 0
        self.blocked_tasks = []
        self.process_state = {}
        self.deadlock_history = []

        self.resource_total = [10, 8, 6]        # R0=CPU slots, R1=MEM units, R2=IO slots
        self.resource_available = [10, 8, 6]
        self.recovery_in_progress = False

        self.memory_blocks = [512]          # fallback until clients connect
        self.memory_total  = [512]
        self.client_mem_labels = ["(no clients)"]  # block label per client
        self.disk_cylinder_max = 200          # fallback until clients connect
        self.disk_head = 53
        self.last_disk_order = []
        self.last_disk_seek = 0

        self.build_ui()
        self.start_server()

        threading.Thread(target=self.scheduler_loop, daemon=True).start()
        threading.Thread(target=self.deadlock_monitor_loop, daemon=True).start()

    # ------------------------------------------------ UI

    def build_ui(self):
        top = ctk.CTkFrame(self.root)
        top.pack(fill="x", padx=10, pady=10)

        self.ip_label = ctk.CTkLabel(top, text="IP: Detecting...")
        self.ip_label.pack(side="left", padx=10, pady=10)

        self.status_label = ctk.CTkLabel(top, text="Waiting for clients...")
        self.status_label.pack(side="right", padx=10, pady=10)

        self.tabs = ctk.CTkTabview(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)

        self.tabs.add("Control")
        self.tabs.add("Devices")
        self.tabs.add("Analytics")
        self.tabs.add("Chat")
        self.tabs.add("Deadlock")
        self.tabs.add("Memory & Disk")

        self.tab1 = self.tabs.tab("Control")
        self.tab2 = self.tabs.tab("Devices")
        self.tab3 = self.tabs.tab("Analytics")
        self.tab4 = self.tabs.tab("Chat")
        self.tab5 = self.tabs.tab("Deadlock")
        self.tab6 = self.tabs.tab("Memory & Disk")

        self.build_tab1()
        self.build_tab2()
        self.build_tab3()
        self.build_tab4()
        self.build_tab5()
        self.build_tab6()


    def build_tab1(self):
        alg = ctk.CTkFrame(self.tab1)
        alg.pack(fill="x", padx=10, pady=8)

        self.cpu_algo = tk.StringVar(value="FCFS")
        self.mem_algo = tk.StringVar(value="FirstFit")
        self.disk_algo = tk.StringVar(value="FCFS")

        ctk.CTkLabel(alg, text="CPU").grid(row=0, column=0, padx=8, pady=8)
        ttk.Combobox(
            alg,
            textvariable=self.cpu_algo,
            values=["FCFS", "SJF", "PRIORITY", "RR"],
            width=12,
            state="readonly"
        ).grid(row=0, column=1)

        ctk.CTkLabel(alg, text="Memory").grid(row=0, column=2, padx=8)
        ttk.Combobox(
            alg,
            textvariable=self.mem_algo,
            values=["FirstFit", "BestFit", "WorstFit", "NextFit"],
            width=12,
            state="readonly"
        ).grid(row=0, column=3)

        ctk.CTkLabel(alg, text="Disk").grid(row=0, column=4, padx=8)
        ttk.Combobox(
            alg,
            textvariable=self.disk_algo,
            values=["FCFS", "SCAN", "CSCAN", "SSTF"],
            width=12,
            state="readonly"
        ).grid(row=0, column=5)

        stats = ctk.CTkFrame(self.tab1)
        stats.pack(fill="x", padx=10, pady=5)

        self.queue_label = ctk.CTkLabel(stats, text="Queue: 0")
        self.queue_label.pack(side="left", padx=15, pady=10)

        self.run_label = ctk.CTkLabel(stats, text="Running: 0")
        self.run_label.pack(side="left", padx=15)

        self.done_label = ctk.CTkLabel(stats, text="Completed: 0")
        self.done_label.pack(side="left", padx=15)

        self.deadlock_label = ctk.CTkLabel(
            stats,
            text="SAFE",
            fg_color="green",
            corner_radius=8,
            width=110
        )
        self.deadlock_label.pack(side="right", padx=15)

        grid = ctk.CTkFrame(self.tab1)
        grid.pack(fill="both", expand=True, padx=10, pady=8)

        grid.grid_columnconfigure((0, 1), weight=1)
        grid.grid_rowconfigure((0, 1), weight=1)

        self.session_list = self.make_box(grid, "Sessions", 0, 0)
        self.queue_list = self.make_box(grid, "Ready Queue", 0, 1)
        self.running_list = self.make_box(grid, "Running", 1, 0)
        self.completed_list = self.make_box(grid, "Completed", 1, 1)

        pf = ctk.CTkFrame(self.tab1)
        pf.pack(fill="both", expand=True, padx=10, pady=8)

        ctk.CTkLabel(
            pf,
            text="Process Details (Queue & Execution)",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=8)

        cols = ("Application", "Process", "Priority", "Worker", "Status")
        self.process_tree = ttk.Treeview(
            pf,
            columns=cols,
            show="headings",
            height=10
        )

        for c in cols:
            self.process_tree.heading(c, text=c)
            self.process_tree.column(c, width=220, anchor="center")

        self.process_tree.pack(fill="both", expand=True, padx=8, pady=8)

    def build_tab2(self):
        cols = (
            "Device", "IP", "CPU", "RAM",
            "Disk", "CPU%", "RAM Used",
            "Disk Used", "State"
        )

        frame = ctk.CTkFrame(self.tab2)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=10)

        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=145, anchor="center")

        self.tree.pack(fill="x", padx=5, pady=5)

        self.resource_frame = ctk.CTkScrollableFrame(
            frame,
            label_text="Per Worker Resources"
        )
        self.resource_frame.pack(fill="both", expand=True, padx=5, pady=10)

    def build_tab3(self):
        # ── Top metrics bar ──────────────────────────────────────────────
        top = ctk.CTkFrame(self.tab3)
        top.pack(fill="x", padx=10, pady=10)

        self.wait_label = ctk.CTkLabel(top, text="Avg Waiting: 0.00 s")
        self.wait_label.pack(side="left", padx=10)

        self.tat_label = ctk.CTkLabel(top, text="Avg Turnaround: 0.00 s")
        self.tat_label.pack(side="left", padx=10)

        self.throughput_label = ctk.CTkLabel(top, text="Throughput: 0.00/s")
        self.throughput_label.pack(side="left", padx=10)

        self.util_label = ctk.CTkLabel(top, text="CPU Utilization: 0%")
        self.util_label.pack(side="left", padx=10)

        # ── Mid section: Gantt (left) + Task history table (right) ───────
        mid = ctk.CTkFrame(self.tab3)
        mid.pack(fill="both", expand=True, padx=10, pady=5)

        left = ctk.CTkFrame(mid)
        left.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        right = ctk.CTkFrame(mid)
        right.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            left,
            text="CPU Gantt Chart  (Recent Completed Processes)",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(pady=(6, 2))

        self.fig, self.ax = plt.subplots(figsize=(8, 3))
        self.fig.patch.set_facecolor("#1e1e2e")
        self.ax.set_facecolor("#1e1e2e")
        self.canvas = FigureCanvasTkAgg(self.fig, master=left)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        ctk.CTkLabel(
            right,
            text="Per-Process Performance History",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(pady=(6, 2))

        hcols = ("Task", "Worker", "Wait (s)", "TAT (s)")
        self.history_tree = ttk.Treeview(
            right,
            columns=hcols,
            show="headings",
            height=10
        )

        for c in hcols:
            self.history_tree.heading(c, text=c)
            self.history_tree.column(c, width=130, anchor="center")

        self.history_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # ── Bottom: full-width system event log ──────────────────────────
        log_frame = ctk.CTkFrame(self.tab3)
        log_frame.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(
            log_frame,
            text="System Event Log",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=8, pady=(6, 2))

        self.log = ctk.CTkTextbox(log_frame, height=140)
        self.log.pack(fill="x", padx=8, pady=(0, 8))
    
    def build_tab4(self):
        frame = ctk.CTkFrame(self.tab4)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            frame,
            text="Group Chat",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(10, 8))

        self.chat_box = ctk.CTkTextbox(frame)
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.chat_box.configure(state="disabled")

        bottom = ctk.CTkFrame(frame)
        bottom.pack(fill="x", padx=10, pady=(0, 10))

        self.chat_entry = ctk.CTkEntry(
            bottom,
            placeholder_text="Type message to all workers..."
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.chat_entry.bind("<Return>", lambda e: self.send_chat_from_coordinator())

        self.send_btn = ctk.CTkButton(
            bottom,
            text="Send",
            width=120,
            command=self.send_chat_from_coordinator
        )
        self.send_btn.pack(side="right")

    def build_tab5(self):
        frame = ctk.CTkFrame(self.tab5)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        top = ctk.CTkFrame(frame)
        top.pack(fill="x", padx=5, pady=5)

        self.deadlock_state = ctk.CTkLabel(
            top,
            text="SAFE",
            fg_color="green",
            corner_radius=8,
            width=140
        )
        self.deadlock_state.pack(side="right", padx=5)

        self.auto_btn = ctk.CTkButton(
            top,
            text="Auto Recover: ON",
            width=170,
            command=self.toggle_auto_recover
        )
        self.auto_btn.pack(side="left", padx=5)

        ctk.CTkButton(
            top,
            text="Generate Deadlock",
            width=170,
            command=self.generate_deadlock_case
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            top,
            text="Reset Monitor",
            width=150,
            command=self.reset_deadlock_monitor
        ).pack(side="left", padx=5)

        info = ctk.CTkFrame(frame)
        info.pack(fill="x", padx=5, pady=5)

        self.res_label = ctk.CTkLabel(
            info,
            text="Available: CPU=10  MEM=8  IO=6"
        )
        self.res_label.pack(side="left", padx=10)

        self.block_label = ctk.CTkLabel(
            info,
            text="Blocked: 0"
        )
        self.block_label.pack(side="left", padx=20)

        # ── Three-column body: Banker | Detection | Recovery ─────────────
        body = ctk.CTkFrame(frame)
        body.pack(fill="both", expand=True, padx=5, pady=5)

        left = ctk.CTkFrame(body)
        left.pack(side="left", fill="both", expand=True, padx=4)

        center = ctk.CTkFrame(body)
        center.pack(side="left", fill="both", expand=True, padx=4)

        right = ctk.CTkFrame(body)
        right.pack(side="left", fill="both", expand=True, padx=4)

        ctk.CTkLabel(
            left,
            text="Banker's Algorithm Prediction",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)

        cols = ("PID", "State", "Alloc", "Need", "Decision")
        self.banker_tree = ttk.Treeview(
            left,
            columns=cols,
            show="headings",
            height=22
        )

        for c in cols:
            self.banker_tree.heading(c, text=c)
            self.banker_tree.column(c, width=95, anchor="center")

        self.banker_tree.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            center,
            text="Detection Log",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)

        self.detect_box = ctk.CTkTextbox(center)
        self.detect_box.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            right,
            text="Recovery Log",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)

        self.recovery_box = ctk.CTkTextbox(right)
        self.recovery_box.pack(fill="both", expand=True, padx=5, pady=5)

    def toggle_auto_recover(self):
        self.deadlock_auto = not self.deadlock_auto

        if self.deadlock_auto:
            self.auto_btn.configure(text="Auto Recover: ON")
        else:
            self.auto_btn.configure(text="Auto Recover: OFF")


    def reset_deadlock_monitor(self):
        self.deadlock_mode = False
        self.blocked_tasks.clear()
        self.deadlock_history.clear()
        self.resource_available = self.resource_total[:]

        for pid in self.process_state:
            if self.process_state[pid]["state"] == "Blocked":
                self.process_state[pid]["state"] = "Queued"

        self.refresh_deadlock_panels()
        self.write_detect_log("Monitor reset")


    def generate_deadlock_case(self):
        with self.lock:
            if self.deadlock_mode or self.recovery_in_progress:
                return
            self.create_deadlock_tasks()
            self.deadlock_mode = True

        self.write_detect_log("Deadlock test jobs inserted into ready queue")
        self.write_detect_log("Waiting for contention to build")
        self.refresh_deadlock_panels()


    def write_recovery_log(self, text):
        def task():
            now = time.strftime("%H:%M:%S")
            self.recovery_box.insert("end", f"[{now}] {text}\n")
            self.recovery_box.see("end")
        self.ui(task)


    def create_deadlock_tasks(self):
        """
        Injects 3 DeadlockJob processes into the READY QUEUE as 'Injected'.
        Each task carries a 'planned_alloc' (resources it will grab when dispatched)
        and a 'planned_need' (what it still needs after grabbing, creating the circular wait).

        Timeline:
          1. Tasks appear in the Banker table as 'Injected' (pending_tasks)
          2. Scheduler picks each one up → dispatch_tasks blocks it with the
             planned allocation → Detection Log shows "X waiting for resource"
          3. All 3 are blocked → C detector fires → Recovery Log shows full procedure
        """
        #  (planned_alloc,  planned_need)  — circular hold-and-wait
        #  Needs deliberately EXCEED total resources [10,8,6] so the
        #  C deadlock-detection algorithm always identifies them as deadlocked.
        circular = [
            ([1, 0, 0], [0, 9, 0]),   # Job1: grabs CPU=1, needs MEM=9  (total MEM=8)
            ([0, 1, 0], [0, 0, 7]),   # Job2: grabs MEM=1, needs IO=7   (total IO=6)
            ([0, 0, 1], [11, 0, 0]),  # Job3: grabs IO=1,  needs CPU=11 (total CPU=10)
        ]

        for i, (planned_alloc, planned_need) in enumerate(circular):
            self.proc_counter += 1
            pid       = f"P{self.proc_counter}"
            max_need  = [planned_alloc[j] + planned_need[j] for j in range(3)]

            task = {
                "pid":           pid,
                "name":          f"DeadlockJob{i+1}",
                "parent":        "Deadlock Generator",
                "duration":      random.randint(4, 8),
                "priority":      1,
                "arrival":       time.time(),
                "max":           max_need[:],
                "alloc":         [0, 0, 0],          # nothing held yet
                "need":          max_need[:],         # full need while in queue
                "planned_alloc": planned_alloc[:],   # will grab this on dispatch
                "planned_need":  planned_need[:],    # will still need this after grab
                "state":         "Queued",
                "memory":        100,
                "disk_requests": random.sample(range(1, 199), 4),
                "mem_block":     -1
            }

            self.pending_tasks.append(task)           # enters the ready queue

            self.process_state[pid] = {
                "state":    "Queued",
                "max":      max_need[:],
                "alloc":    [0, 0, 0],
                "need":     max_need[:],
                "decision": "Injected",               # shows 'Injected' in table
                "mem_block": -1,
                "memory":   task["memory"]
            }


    def write_detect_log(self, text):
        def task():
            now = time.strftime("%H:%M:%S")
            self.detect_box.insert("end", f"[{now}] {text}\n")
            self.detect_box.see("end")
        self.ui(task)


    def refresh_deadlock_ui(self):
        self.res_label.configure(
            text=f"Available: CPU={self.resource_available[0]}  MEM={self.resource_available[1]}  IO={self.resource_available[2]}"
        )

        blocked = sum(
            1 for p in self.process_state.values()
            if p["state"] == "Blocked"
        )

        self.block_label.configure(text=f"Blocked: {blocked}")

        if self.recovery_in_progress:
            self.deadlock_state.configure(
                text="RECOVERING",
                fg_color="orange"
            )
        elif self.deadlock_mode:
            self.deadlock_state.configure(
                text="DEADLOCK",
                fg_color="red"
            )
        else:
            self.deadlock_state.configure(
                text="SAFE",
                fg_color="green"
            )

        rows = self.banker_tree.get_children()
        if rows:
            self.banker_tree.delete(*rows)

        def sort_key(x):
            try:
                return int(x[1:])
            except:
                return 9999

        for pid in sorted(self.process_state.keys(), key=sort_key):
            p = self.process_state[pid]

            self.banker_tree.insert(
                "",
                "end",
                values=(
                    pid,
                    p["state"],
                    str(p["alloc"]),
                    str(p["need"]),
                    p.get("decision", "-")
                )
            )
    def make_box(self, parent, title, r, c):
        box = ctk.CTkFrame(parent)
        box.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)

        ctk.CTkLabel(
            box,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=5)

        lb = tk.Listbox(box, height=8)
        lb.pack(fill="both", expand=True, padx=5, pady=5)
        return lb

    # ------------------------------------------------ Utility

    def run_sim(self, args):
        exe = os.path.join(os.path.dirname(__file__), "c_modules", "sim_runner.exe")
        try:
            r = subprocess.run([exe] + args, capture_output=True, text=True, timeout=5)
            return r.stdout.strip()
        except Exception as e:
            print("run_sim error:", e)
            return ""

    def refresh_visuals(self):
        """Refresh the dedicated Memory & Disk tab visualisations."""
        self.refresh_mem_disk_tab()


    def ui(self, fn):
        self.root.after(0, fn)

    def write_log(self, msg):
        def task():
            self.log.insert("end", msg + "\n")
            self.log.see("end")
        self.ui(task)

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except:
            ip = "127.0.0.1"
        s.close()
        return ip

    # ------------------------------------------------ Server

    def start_server(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(("0.0.0.0", PORT))
        self.server.listen(20)

        ip = self.get_local_ip()
        self.ip_label.configure(text=f"IP: {ip}:{PORT}")
        self.write_log("Coordinator started")

        threading.Thread(target=self.accept_clients, daemon=True).start()

    def accept_clients(self):
        while True:
            sock, addr = self.server.accept()
            threading.Thread(
                target=self.handle_client,
                args=(sock, addr),
                daemon=True
            ).start()

    def handle_client(self, sock, addr):
        buffer = ""

        while True:
            try:
                data = sock.recv(4096).decode()

                if not data:
                    break

                buffer += data

                while buffer:
                    try:
                        msg, index = json.JSONDecoder().raw_decode(buffer)
                        buffer = buffer[index:].lstrip()

                    except json.JSONDecodeError:
                        break

                    msg_type = msg.get("type", "")

                    if msg_type == "join":
                        self.add_client(sock, addr[0], msg)

                    elif msg_type == "session_start":
                        self.add_session(msg)

                    elif msg_type == "session_stop":
                        self.remove_session(msg)

                    elif msg_type == "task_request":
                        self.add_task(msg)

                    elif msg_type == "task_done":
                        self.finish_task(msg)

                    elif msg_type == "chat":
                        self.receive_chat(msg)

            except Exception as e:
                print("CLIENT ERROR:", addr, e)
                break

        with self.lock:
            self.clients = [c for c in self.clients if c["socket"] != sock]

        # Rebuild cluster resources now that one client is gone
        self._rebuild_cluster_resources()

        self.ui(self.update_table)
        self.ui(
            lambda: self.status_label.configure(
                text=f"{len(self.clients)} Clients Connected"
            )
        )

        try:
            sock.close()
        except:
            pass
    # ------------------------------------------------ Data actions


    def send_chat_from_coordinator(self):
        text = self.chat_entry.get().strip()

        if text == "":
            return

        self.receive_chat({
            "sender": "Coordinator",
            "message": text
        })

        self.chat_entry.delete(0, "end")

    def receive_chat(self, msg):
        sender = msg.get("sender", "Unknown")
        message = msg.get("message", "")

        def task():
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"[{sender}] {message}\n")
            self.chat_box.see("end")
            self.chat_box.configure(state="disabled")

        self.ui(task)

        packet = json.dumps({
            "type": "chat",
            "sender": sender,
            "message": message
        }).encode()

        with self.lock:
            for c in self.clients:
                try:
                    c["socket"].send(packet)
                except:
                    pass

    def broadcast_chat(self, msg):
        dead = []

        for c in self.clients:
            try:
                c["socket"].send(json.dumps(msg).encode())
            except:
                dead.append(c)

        if dead:
            with self.lock:
                for d in dead:
                    if d in self.clients:
                        self.clients.remove(d)
                        
    def _rebuild_cluster_resources(self):
        """Rebuild memory pool and disk cylinder range from connected clients.

        Memory : one block per client  =  client's RAM (GB) × 1024 MB.
        Disk   : cylinder range 1 – sum_of_all_client_disk_GB.
        Called whenever a client joins or leaves.
        """
        with self.lock:
            if not self.clients:
                self.memory_blocks      = [512]
                self.memory_total       = [512]
                self.client_mem_labels  = ["(no clients)"]
                self.disk_cylinder_max  = 200
                return

            new_total  = [c["ram"] * 1024 for c in self.clients]   # MB per client
            new_labels = [c["device"]       for c in self.clients]

            # Preserve used space for existing blocks by device name
            old_label_map = dict(zip(self.client_mem_labels, self.memory_blocks))
            old_total_map = dict(zip(self.client_mem_labels, self.memory_total))

            new_blocks = []
            for lbl, tot in zip(new_labels, new_total):
                if lbl in old_label_map and lbl in old_total_map:
                    # Keep same used-space ratio as before
                    used_old = old_total_map[lbl] - old_label_map[lbl]
                    new_blocks.append(max(0, tot - min(used_old, tot)))
                else:
                    new_blocks.append(tot)  # fresh client — full block

            self.memory_blocks     = new_blocks
            self.memory_total      = new_total
            self.client_mem_labels = new_labels

            # Disk cylinders scale with total connected storage
            total_disk_gb = sum(c["disk"] for c in self.clients)
            self.disk_cylinder_max = max(200, total_disk_gb)

        self.write_log(
            f"Cluster resources rebuilt: "
            f"memory = {sum(self.memory_total)} MB across "
            f"{len(self.clients)} node(s), "
            f"disk cylinders = 0–{self.disk_cylinder_max}"
        )
        self.ui(self.refresh_visuals)

    def add_client(self, sock, ip, msg):
        with self.lock:
            self.clients.append({
                "socket":    sock,
                "device":    msg["device"],
                "ip":        ip,
                "cpu":       msg["cpu"],
                "ram":       msg["ram"],
                "disk":      msg["disk"],
                "used_cpu":  0,
                "used_ram":  0,
                "used_disk": 0,
                "busy":      False,
                "load":      0
            })

        # Update memory pool + disk range from real client data
        self._rebuild_cluster_resources()

        self.write_log(
            f"Client joined: {msg['device']}  "
            f"RAM={msg['ram']} GB  Disk={msg['disk']} GB  CPU={msg['cpu']} cores"
        )

        self.ui(self.update_table)
        self.ui(
            lambda: self.status_label.configure(
                text=f"{len(self.clients)} Clients Connected"
            )
        )

    def add_session(self, msg):
        s = f'{msg["app"]} -> {msg["device"]}'
        if s not in self.sessions:
            self.sessions.append(s)
        self.ui(self.refresh_sessions)

    def remove_session(self, msg):
        s = f'{msg["app"]} -> {msg["device"]}'
        if s in self.sessions:
            self.sessions.remove(s)
        self.ui(self.refresh_sessions)

    def add_task(self, msg):
        self.proc_counter += 1
        pid = f"P{self.proc_counter}"

        max_need = [
            random.randint(1, 4),
            random.randint(1, 3),
            random.randint(1, 3)
        ]

        alloc = [0, 0, 0]

        task = {
            "pid": pid,
            "name": msg["task"],
            "parent": msg["parent"],
            "duration": msg["duration"],
            "priority": random.randint(1, 5),
            "arrival": time.time(),
            "max": max_need,
            "alloc": alloc,
            "need": max_need[:],
            "state": "Queued",
            "memory": random.randint(
                max(10, min(self.memory_blocks) // 10),
                max(20, min(self.memory_blocks) // 5)
            ) if self.memory_blocks else random.randint(20, 100),
            "disk_requests": random.sample(
                range(1, max(2, self.disk_cylinder_max)),
                min(random.randint(5, 8), max(1, self.disk_cylinder_max - 1))
            ),
            "mem_block": -1
        }

        with self.lock:
            self.pending_tasks.append(task)

            self.process_state[pid] = {
                "state": "Queued",
                "max": max_need[:],
                "alloc": alloc[:],
                "need": max_need[:],
                "decision": "Waiting",
                "mem_block": -1,
                "memory": task["memory"]
            }

        self.ui(self.refresh_queue)
        self.ui(self.refresh_deadlock_ui)

        def add_row():
            self.process_tree.insert(
                "",
                "end",
                values=(
                    task["parent"],
                    f'{pid} {task["name"]}',
                    task["priority"],
                    "-",
                    "Queued"
                )
            )

        self.ui(add_row)
        self.ui(self.refresh_deadlock_panels)

    # ------------------------------------------------ Refresh lists

    def refresh_sessions(self):
        self.session_list.delete(0, "end")
        for s in self.sessions:
            self.session_list.insert("end", s)

    def refresh_queue(self):
        """Refresh the Ready Queue listbox, sorted to reflect the active
        scheduling algorithm so the user can see its effect visually."""
        algo = self.cpu_algo.get() if hasattr(self, 'cpu_algo') else "FCFS"

        tasks = list(self.pending_tasks)  # snapshot – do NOT modify original

        if algo == "SJF":
            tasks = sorted(tasks, key=lambda t: t["duration"])
        elif algo == "PRIORITY":
            tasks = sorted(tasks, key=lambda t: (t["priority"], t["duration"]))
        # FCFS and RR: keep arrival order (natural list order)

        self.queue_list.delete(0, "end")
        for t in tasks:
            if algo == "SJF":
                label = f'{t["name"]}  burst={t["duration"]}s'
            elif algo == "PRIORITY":
                label = f'{t["name"]}  pri={t["priority"]}'
            elif algo == "RR":
                label = f'{t["name"]}  (RR)'
            else:
                label = f'{t["name"]}  ({t["duration"]}s)'
            self.queue_list.insert("end", label)

        self.queue_label.configure(text=f"Queue: {len(self.pending_tasks)}")

    def refresh_running(self):
        self.running_list.delete(0, "end")
        for r in self.running_tasks:
            self.running_list.insert("end", r)

    def refresh_completed(self):
        self.completed_list.delete(0, "end")
        for x in self.completed_tasks[-20:]:
            self.completed_list.insert("end", x)

    # ------------------------------------------------ Scheduler

    def deadlock_monitor_loop(self):
        """Delegates deadlock detection to C sim_runner.exe detect_deadlock().
        NOTE: subprocess call is made OUTSIDE the lock to avoid contention.
        """
        while True:
            try:
                R = 3
                sim_args   = None
                all_pids   = []
                active_len = 0

                # ── Phase 1: snapshot state under lock ─────────────────────
                with self.lock:
                    all_pids = [
                        pid for pid, d in self.process_state.items()
                        if d["state"] not in ("Completed", "Aborted")
                    ]
                    active_len = sum(
                        1 for pid, d in self.process_state.items()
                        if d["state"] in ("Running", "Queued", "Blocked")
                    )

                    if all_pids:
                        P         = len(all_pids)
                        avail_csv = ",".join(str(x) for x in self.resource_available)
                        alloc_rows, req_rows = [], []
                        for pid in all_pids:
                            d = self.process_state[pid]
                            alloc_rows.extend(d.get("alloc", [0, 0, 0]))
                            if d["state"] == "Blocked":
                                req_rows.extend(d.get("need", [0, 0, 0]))
                            else:
                                req_rows.extend([0, 0, 0])
                        sim_args = [
                            "deadlock", str(P), str(R),
                            avail_csv,
                            ",".join(str(x) for x in alloc_rows),
                            ",".join(str(x) for x in req_rows)
                        ]

                # ── Phase 2: C call OUTSIDE the lock ───────────────────────
                n_dead    = 0
                dead_pids = []
                if sim_args:
                    out   = self.run_sim(sim_args)
                    parts = out.split("|")
                    n_dead = int(parts[1]) if len(parts) >= 2 else 0
                    if n_dead > 0 and len(parts) >= 3:
                        dead_indices = [int(x) for x in parts[2].split(",") if x]
                        dead_pids   = [
                            all_pids[i] for i in dead_indices
                            if i < len(all_pids)
                        ]

                # ── Phase 3: act on result (no lock needed for UI/thread) ──
                if n_dead > 0:
                    self.write_detect_log(
                        f"C deadlock detected ({n_dead} procs): "
                        + ", ".join(dead_pids)
                    )
                    if self.deadlock_auto and not self.recovery_in_progress:
                        threading.Thread(
                            target=self.recover_deadlock_live,
                            daemon=True
                        ).start()
                else:
                    with self.lock:
                        if self.deadlock_mode and active_len == 0:
                            self.deadlock_mode = False

                self.refresh_deadlock_panels()

            except Exception as e:
                print("monitor error:", e)

            time.sleep(2)

    def recover_deadlock_live(self):
        self.recovery_in_progress = True
        self.write_recovery_log("=" * 36)
        self.write_recovery_log("DEADLOCK RECOVERY INITIATED")
        time.sleep(0.5)

        with self.lock:
            blocked_pids = [
                pid for pid, d in self.process_state.items()
                if d["state"] == "Blocked"
            ]

        if not blocked_pids:
            self.write_recovery_log("No blocked processes — nothing to recover.")
            self.recovery_in_progress = False
            return

        self.write_recovery_log(f"Blocked processes: {', '.join(blocked_pids)}")
        time.sleep(0.5)

        # Select victim: pick the one with the largest total allocation
        with self.lock:
            victim = max(
                blocked_pids,
                key=lambda p: sum(self.process_state[p].get("alloc", [0,0,0]))
            )

        self.write_recovery_log(f"Victim selected: {victim}  (highest resource holder)")
        time.sleep(0.8)

        # ── Abort victim ────────────────────────────────────────────────────
        with self.lock:
            self.process_state[victim]["state"]    = "Aborted"
            self.process_state[victim]["decision"] = "Aborted (victim)"
            # Release victim's allocations back to pool
            victim_alloc = self.process_state[victim].get("alloc", [0, 0, 0])
            for i in range(3):
                self.resource_available[i] = min(
                    self.resource_total[i],
                    self.resource_available[i] + victim_alloc[i]
                )
            self.process_state[victim]["alloc"] = [0, 0, 0]
            # Remove victim from blocked_tasks list
            self.blocked_tasks = [
                t for t in self.blocked_tasks if t["pid"] != victim
            ]

        self.write_recovery_log(
            f"Aborted {victim} — released CPU={victim_alloc[0]}  "
            f"MEM={victim_alloc[1]}  IO={victim_alloc[2]}"
        )
        self.refresh_deadlock_panels()
        time.sleep(0.8)

        # ── Recover remaining blocked processes ──────────────────────────────
        self.write_recovery_log("Releasing remaining blocked processes...")

        recovered = []
        with self.lock:
            # Snapshot the blocked list before mutating
            still_blocked = [t for t in self.blocked_tasks if t["pid"] != victim]

            for task in still_blocked:
                pid = task["pid"]
                d   = self.process_state.get(pid, {})
                if d.get("state") == "Blocked":
                    # Release this process's held resources too
                    held = d.get("alloc", [0, 0, 0])
                    for i in range(3):
                        self.resource_available[i] = min(
                            self.resource_total[i],
                            self.resource_available[i] + held[i]
                        )
                    # Reset process for re-execution
                    d["state"]    = "Queued"
                    d["decision"] = "Recovered"
                    d["alloc"]    = [0, 0, 0]
                    d["need"]     = d.get("max", [0, 0, 0])[:]
                    # Reset task dict too
                    task["state"] = "Queued"
                    task["alloc"] = [0, 0, 0]
                    task["need"]  = d["need"][:]
                    # Re-insert into pending queue so it can actually run
                    self.pending_tasks.append(task)
                    recovered.append(pid)

            self.blocked_tasks.clear()
            self.deadlock_mode = False

        if recovered:
            self.write_recovery_log(f"Re-queued: {', '.join(recovered)}")
        self.write_recovery_log(
            f"Resources now available: CPU={self.resource_available[0]}  "
            f"MEM={self.resource_available[1]}  IO={self.resource_available[2]}"
        )

        self.refresh_deadlock_panels()
        time.sleep(0.5)

        self.write_recovery_log("Recovery complete — system resumed.")
        self.write_recovery_log("=" * 36)
        self.recovery_in_progress = False

    def scheduler_loop(self):
        while True:
            try:
                self.dispatch_tasks()
                self.ui(self.update_stats)
            except:
                pass
            time.sleep(0.5)

    def choose_task(self):
        """Delegates scheduling decision to C sim_runner.exe."""
        if not self.pending_tasks:
            return None

        algo = self.cpu_algo.get()
        n    = len(self.pending_tasks)

        bursts     = ",".join(str(t["duration"]) for t in self.pending_tasks)
        priorities = ",".join(str(t["priority"]) for t in self.pending_tasks)

        out = self.run_sim(["scheduler", algo, bursts, priorities, str(self.rr_index)])
        # out format: SCHED|<idx>
        try:
            idx = int(out.split("|")[1])
            idx = max(0, min(idx, n - 1))  # clamp
        except:
            idx = 0

        # Advance RR pointer so next call gets a different process
        if algo == "RR":
            self.rr_index = idx

        return self.pending_tasks.pop(idx)

    def choose_worker(self):
        free = [c for c in self.clients if not c["busy"]]
        if not free:
            return None

        return min(
            free,
            key=lambda x: (x["load"], x["used_cpu"])
        )

    def _build_bankers_args(self, extra_pid=None, extra_task=None):
        """
        Build argument lists for the C Banker's safety-check command.

        CORRECT OS interpretation: only RUNNING processes have actual resource
        allocations. Queued / Blocked processes hold zero resources, so they
        must NOT be included in the Banker's matrix — doing so inflates the
        apparent demand and makes the system look permanently unsafe.

        We include:
          - All processes in state "Running"  (they hold real allocations)
          - The ONE proposed new process (extra_pid) as if it were just granted

        Returns (P, R, avail_csv, max_csv, alloc_csv) or None if nothing to check.
        """
        R = 3

        # Only running processes have actual allocations
        pids = [
            pid for pid, d in self.process_state.items()
            if d["state"] == "Running"
        ]

        # Add the proposed process being evaluated
        if extra_pid and extra_pid not in pids:
            pids.append(extra_pid)

        if not pids:
            return None

        P    = len(pids)
        avail = self.resource_available[:]

        max_flat   = []
        alloc_flat = []

        for pid in pids:
            d = self.process_state.get(pid, {})
            if pid == extra_pid and extra_task:
                # Simulate granting this process its full need
                max_flat.extend(extra_task.get("max",   [0, 0, 0]))
                alloc_flat.extend(extra_task.get("need", [0, 0, 0]))
            else:
                max_flat.extend(d.get("max",   [0, 0, 0]))
                alloc_flat.extend(d.get("alloc", [0, 0, 0]))

        return (
            str(P),
            str(R),
            ",".join(str(x) for x in avail),
            ",".join(str(x) for x in max_flat),
            ",".join(str(x) for x in alloc_flat),
        )

    def dispatch_tasks(self):
        """Dispatch one task per loop iteration.

        All subprocess (C) calls happen OUTSIDE the lock so that
        handle_client() can still process task_done messages concurrently.
        """
        while True:
            if self.recovery_in_progress:
                return

            # ── PHASE 1: pick worker + snapshot scheduler inputs ──────────
            with self.lock:
                worker = self.choose_worker()
                if not worker or not self.pending_tasks:
                    return

                algo       = self.cpu_algo.get()
                n          = len(self.pending_tasks)
                bursts_csv = ",".join(str(t["duration"]) for t in self.pending_tasks)
                prios_csv  = ",".join(str(t["priority"])  for t in self.pending_tasks)
                rr_idx     = self.rr_index

            # ── PHASE 2: scheduler C call (outside lock) ──────────────────
            sched_out = self.run_sim(
                ["scheduler", algo, bursts_csv, prios_csv, str(rr_idx)]
            )
            try:
                chosen_idx = int(sched_out.split("|")[1])
                chosen_idx = max(0, min(chosen_idx, n - 1))
            except:
                chosen_idx = 0

            # ── PHASE 3: pop task + snapshot inputs for remaining C calls ─
            with self.lock:
                # re-check: state may have changed between phases
                worker = self.choose_worker()
                if not worker or not self.pending_tasks:
                    return

                chosen_idx = min(chosen_idx, len(self.pending_tasks) - 1)
                if algo == "RR":
                    self.rr_index = chosen_idx

                task = self.pending_tasks.pop(chosen_idx)
                pid  = task["pid"]

                # Early exits that don't need C calls
                if pid in self.process_state and \
                        self.process_state[pid]["state"] == "Aborted":
                    continue

                if self.deadlock_mode and "DeadlockJob" in task["name"]:
                    # Apply the planned partial allocation — this process now
                    # HOLDS some resources and WAITS for others (circular wait)
                    planned = task.get("planned_alloc", [1, 1, 1])
                    p_need  = task.get("planned_need",  [1, 1, 1])
                    for i in range(3):
                        self.resource_available[i] = max(
                            0, self.resource_available[i] - planned[i]
                        )
                    task["alloc"]  = planned[:]
                    task["need"]   = p_need[:]
                    task["state"]  = "Blocked"
                    self.process_state[pid]["alloc"]    = planned[:]
                    self.process_state[pid]["need"]     = p_need[:]
                    self.process_state[pid]["state"]    = "Blocked"
                    self.process_state[pid]["decision"] = "Circular Wait"
                    self.blocked_tasks.append(task)
                    self.write_detect_log(
                        f"{pid} ({task['name']}) grabbed "
                        f"CPU={planned[0]} MEM={planned[1]} IO={planned[2]}, "
                        f"now waiting for CPU={p_need[0]} MEM={p_need[1]} IO={p_need[2]}"
                    )
                    self.ui(self.refresh_deadlock_ui)
                    # When all 3 deadlock jobs are blocked, trigger recovery directly
                    blocked_dl = [
                        t for t in self.blocked_tasks
                        if "DeadlockJob" in t.get("name", "")
                    ]
                    if len(blocked_dl) >= 3 and not self.recovery_in_progress:
                        self.write_detect_log(
                            "All 3 DeadlockJobs in circular wait — triggering recovery"
                        )
                        threading.Thread(
                            target=self.recover_deadlock_live,
                            daemon=True
                        ).start()
                    continue

                # Snapshot everything C needs while we hold the lock
                mem_algo_val   = self.mem_algo.get()
                disk_algo_val  = self.disk_algo.get()
                mem_blocks_csv = ",".join(str(x) for x in self.memory_blocks)
                disk_head_val  = self.disk_head
                disk_reqs_csv  = ",".join(
                    str(x) for x in task.get("disk_requests", [])
                )
                mem_size       = task.get("memory", 100)
                nf_pos         = self.next_fit_pos   # for NextFit persistence
                banker_args    = self._build_bankers_args(
                    extra_pid=pid, extra_task=task
                )

            # ── PHASE 4: memory + disk + bankers calls (all outside lock) ─
            out_mem  = self.run_sim(
                ["memory", mem_algo_val, mem_blocks_csv, str(mem_size),
                 str(nf_pos)]   # last arg = NextFit last position
            )
            out_disk = self.run_sim(
                ["disk", disk_algo_val, str(disk_head_val), disk_reqs_csv,
                 str(self.disk_cylinder_max)]
            )
            if banker_args:
                out_bank = self.run_sim(["bankers"] + list(banker_args))
                is_safe  = out_bank.startswith("BANKERS|SAFE")
            else:
                is_safe = True

            # ── PHASE 5: apply all results back under lock ─────────────────
            with self.lock:
                # Memory result
                if out_mem.startswith("MEMORY|0"):
                    task["state"]                        = "Blocked"
                    self.process_state[pid]["state"]     = "Blocked"
                    self.process_state[pid]["decision"]  = "Waiting Memory"
                    self.blocked_tasks.append(task)
                    self.write_detect_log(f"{pid} waiting for memory")
                    self.ui(self.refresh_deadlock_ui)
                    continue
                else:
                    parts = out_mem.split("|")
                    if len(parts) >= 3:
                        mem_idx = int(parts[1]) - 1
                        rem     = int(parts[2])
                        task["mem_block"]                     = mem_idx
                        self.memory_blocks[mem_idx]           = rem
                        self.process_state[pid]["mem_block"] = mem_idx
                        # Update NextFit position if that algo is active
                        if len(parts) >= 4:
                            self.next_fit_pos = int(parts[3])

                # Disk result
                parts = out_disk.split("|")
                if len(parts) >= 3:
                    parsed_order = [int(x) for x in parts[1].split(",") if x]
                    seek         = int(parts[2])
                    self.last_disk_order = parsed_order
                    self.last_disk_seek  = seek
                    if parsed_order:
                        # Save head BEFORE updating so chart can show start position
                        self._last_dispatch_head = disk_head_val
                        self.disk_head = parsed_order[-1]
                    task["duration"] += min(3, max(0, seek // 400))  # max +3s overhead

                # Re-check aborted (could have been aborted during C calls)
                if pid in self.process_state and \
                        self.process_state[pid]["state"] == "Aborted":
                    continue

                # Banker's result
                if not is_safe:
                    task["state"]                        = "Blocked"
                    self.process_state[pid]["state"]     = "Blocked"
                    self.process_state[pid]["decision"]  = "Unsafe State"
                    self.blocked_tasks.append(task)
                    self.write_detect_log(f"{pid} unsafe by Banker's – blocked")
                    self.ui(self.refresh_deadlock_ui)
                    continue

                # Grant resources
                need = task["need"][:]
                for i in range(3):
                    self.resource_available[i] -= need[i]
                    task["alloc"][i]           += need[i]
                    task["need"][i]             = 0

                self.process_state[pid]["alloc"]    = task["alloc"][:]
                self.process_state[pid]["need"]     = task["need"][:]
                self.process_state[pid]["state"]    = "Running"
                self.process_state[pid]["decision"] = "Granted"

                worker["busy"]      = True
                worker["load"]     += 1
                worker["used_cpu"]  = random.randint(45, 95)
                worker["used_ram"]  = min(worker["ram"],  random.randint(1, worker["ram"]))
                worker["used_disk"] = min(worker["disk"], random.randint(5, worker["disk"]))

            # ── PHASE 6: send to worker (no lock needed) ──────────────────
            try:
                worker["socket"].send(json.dumps({
                    "type":     "run_task",
                    "task":     task["name"],
                    "duration": task["duration"]
                }).encode())
            except:
                with self.lock:
                    worker["busy"] = False
                return

            self.running_tasks.append(
                f'{pid} {task["name"]} -> {worker["device"]}'
            )
            self.mark_running(task, worker["device"])
            self.ui(self.refresh_queue)
            self.ui(self.refresh_running)
            self.ui(self.update_table)
            self.ui(self.refresh_deadlock_panels)
            self.ui(self.refresh_visuals)

    # ------------------------------------------------ Completion

    def mark_running(self, task, worker):
        def fn():
            for row in self.process_tree.get_children():
                vals = self.process_tree.item(row, "values")
                if vals[1] == task["name"] and vals[4] == "Queued":
                    self.process_tree.item(
                        row,
                        values=(vals[0], vals[1], vals[2], worker, "Running")
                    )
                    break
        self.ui(fn)

    def finish_task(self, msg):
        dev = msg["device"]
        task_name = msg["task"]

        wait = round(random.uniform(0.5, 3.0), 2)
        tat = round(wait + random.uniform(2.0, 6.0), 2)

        released_pid = None

        with self.lock:
            for c in self.clients:
                if c["device"] == dev:
                    c["busy"] = False
                    c["used_cpu"] = 0
                    c["used_ram"] = 0
                    c["used_disk"] = 0

            # Find running task by name/device
            remove_row = None
            for item in self.running_tasks:
                if task_name in item and dev in item:
                    remove_row = item
                    break

            if remove_row:
                self.running_tasks.remove(remove_row)

                parts = remove_row.split()
                if parts:
                    released_pid = parts[0]

            self.completed += 1

            # Release resources
            if released_pid and released_pid in self.process_state:
                alloc = self.process_state[released_pid]["alloc"]

                for i in range(3):
                    self.resource_available[i] += alloc[i]

                self.process_state[released_pid]["alloc"] = [0, 0, 0]
                self.process_state[released_pid]["need"] = [0, 0, 0]
                self.process_state[released_pid]["state"] = "Completed"
                self.process_state[released_pid]["decision"] = "Finished"

                idx = self.process_state[released_pid].get("mem_block", -1)
                if idx >= 0:
                    self.memory_blocks[idx] += self.process_state[released_pid].get("memory", 0)

        self.total_wait += wait
        self.total_tat += tat

        self.completed_tasks.append(f"{task_name} by {dev}")
        self.gantt.append((task_name, random.randint(2, 5)))

        def update_rows():
            for row in self.process_tree.get_children():
                vals = self.process_tree.item(row, "values")

                if vals[3] == dev and vals[4] == "Running":
                    self.process_tree.item(
                        row,
                        values=(vals[0], vals[1], vals[2], vals[3], "Completed")
                    )
                    break

            self.history_tree.insert(
                "",
                "end",
                values=(task_name, dev, wait, tat)
            )

        self.ui(update_rows)
        self.ui(self.refresh_running)
        self.ui(self.refresh_completed)
        self.ui(self.update_table)
        self.ui(self.update_stats)
        self.ui(self.update_gantt)
        self.ui(self.refresh_deadlock_panels)
        self.ui(self.refresh_visuals)

        self.write_log(f"{task_name} completed by {dev}")

        # Try blocked tasks again after release
        self.retry_blocked_tasks()
    
    def retry_blocked_tasks(self):
        with self.lock:
            if not self.blocked_tasks:
                return

            moved = []

            for task in self.blocked_tasks:
                pid = task["pid"]

                can_run = True
                for i in range(3):
                    if task["need"][i] > self.resource_available[i]:
                        can_run = False
                        break

                if can_run:
                    task["state"] = "Queued"
                    self.process_state[pid]["state"] = "Queued"
                    self.process_state[pid]["decision"] = "Requeued"
                    self.pending_tasks.append(task)
                    moved.append(task)

            for task in moved:
                self.blocked_tasks.remove(task)

            self.ui(self.refresh_queue)
            self.ui(self.refresh_deadlock_panels)

    # ------------------------------------------------ Tables

    def update_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for c in self.clients:
            self.tree.insert("", "end", values=(
                c["device"],
                c["ip"],
                c["cpu"],
                f'{c["ram"]} GB',
                f'{c["disk"]} GB',
                f'{c["used_cpu"]}%',
                f'{c["used_ram"]}/{c["ram"]}',
                f'{c["used_disk"]}/{c["disk"]}',
                "Running" if c["busy"] else "Idle"
            ))

        self.draw_resource_cards()

    def draw_resource_cards(self):
        for w in self.resource_frame.winfo_children():
            w.destroy()

        for c in self.clients:
            card = ctk.CTkFrame(self.resource_frame)
            card.pack(fill="x", padx=5, pady=5)

            ctk.CTkLabel(
                card,
                text=c["device"],
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(anchor="w", padx=10, pady=5)

            self.make_bar(card, "CPU", 100, c["used_cpu"])
            self.make_bar(card, "RAM", c["ram"], c["used_ram"])
            self.make_bar(card, "Disk", c["disk"], c["used_disk"])

    def make_bar(self, parent, title, total, used):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=3)

        ctk.CTkLabel(row, text=title, width=50).pack(side="left")

        bar = ctk.CTkProgressBar(row)
        bar.pack(side="left", fill="x", expand=True, padx=10)
        bar.set(0 if total == 0 else used / total)

        ctk.CTkLabel(row, text=f"{used}/{total}", width=70).pack(side="right")

    # ------------------------------------------------ Metrics

    def update_stats(self):
        running = len([c for c in self.clients if c["busy"]])

        self.run_label.configure(text=f"Running: {running}")
        self.done_label.configure(text=f"Completed: {self.completed}")

        if running == len(self.clients) and self.pending_tasks and self.clients:
            self.deadlock_label.configure(text="WAITING", fg_color="orange")
        elif not self.clients and self.pending_tasks:
            self.deadlock_label.configure(text="NO WORKERS", fg_color="red")
        else:
            self.deadlock_label.configure(text="SAFE", fg_color="green")

        avg_wait = self.total_wait / self.completed if self.completed else 0
        avg_tat = self.total_tat / self.completed if self.completed else 0

        elapsed = max(1, time.time() - self.start_clock)
        throughput = self.completed / elapsed

        util = 0
        if self.clients:
            util = sum(c["used_cpu"] for c in self.clients) / len(self.clients)

        self.wait_label.configure(text=f"Avg Waiting: {avg_wait:.2f} s")
        self.tat_label.configure(text=f"Avg Turnaround: {avg_tat:.2f} s")
        self.throughput_label.configure(text=f"Throughput: {throughput:.2f}/s")
        self.util_label.configure(text=f"CPU Utilization: {util:.0f}%")

    # ------------------------------------------------ Gantt

    def update_gantt(self):
        self.ax.clear()

        start = 0
        labels = list(self.gantt)

        for task, dur in labels:
            self.ax.barh(0, dur, left=start, height=0.45)
            self.ax.text(
                start + dur / 2,
                0,
                task[:8],
                ha="center",
                va="center",
                fontsize=8,
                color="white"
            )
            start += dur

        self.ax.set_xlim(0, max(10, start))
        self.ax.set_title("Recent Completed Processes")
        self.ax.set_yticks([])
        self.ax.grid(axis="x", alpha=0.3)
        self.canvas.draw()
    
    def refresh_deadlock_panels(self):
        def task():
            self.refresh_deadlock_ui()
        self.ui(task)

    # ------------------------------------------------ Tab 6: Memory & Disk

    def build_tab6(self):
        """Dedicated Memory Allocation + Disk Scheduling visualisation tab."""
        frame = ctk.CTkFrame(self.tab6)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Header info bar ─────────────────────────────────────────────
        info = ctk.CTkFrame(frame)
        info.pack(fill="x", padx=5, pady=(5, 0))

        ctk.CTkLabel(
            info,
            text="Memory & Disk Visualisations",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=12, pady=8)

        self.mem_algo_label = ctk.CTkLabel(
            info, text="Memory Algorithm: FirstFit"
        )
        self.mem_algo_label.pack(side="left", padx=20)

        self.disk_algo_label = ctk.CTkLabel(
            info, text="Disk Algorithm: FCFS"
        )
        self.disk_algo_label.pack(side="left", padx=20)

        self.disk_head_label = ctk.CTkLabel(
            info, text="Disk Head: 53"
        )
        self.disk_head_label.pack(side="left", padx=20)

        self.total_seek_label = ctk.CTkLabel(
            info, text="Total Seek: 0"
        )
        self.total_seek_label.pack(side="left", padx=20)

        # ── Body: two side-by-side panels ────────────────────────────────
        body = ctk.CTkFrame(frame)
        body.pack(fill="both", expand=True, padx=5, pady=8)

        # Left: Memory allocation chart
        mem_panel = ctk.CTkFrame(body)
        mem_panel.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self.mem_panel_title = ctk.CTkLabel(
            mem_panel,
            text="Memory Block Allocation  (per connected node)",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.mem_panel_title.pack(pady=(6, 2))

        self.fig_mem, self.ax_mem = plt.subplots(figsize=(6, 4))
        self.fig_mem.patch.set_facecolor("#1e1e2e")
        self.ax_mem.set_facecolor("#2a2a3e")
        self.canvas_mem = FigureCanvasTkAgg(self.fig_mem, master=mem_panel)
        self.canvas_mem.get_tk_widget().pack(fill="both", expand=True)

        # Memory block table beneath the chart
        mem_tbl_frame = ctk.CTkFrame(mem_panel)
        mem_tbl_frame.pack(fill="x", padx=5, pady=(4, 6))

        mtcols = ("Node", "RAM (GB)", "Total (MB)", "Used (MB)", "Free (MB)", "% Used")
        self.mem_table = ttk.Treeview(
            mem_tbl_frame, columns=mtcols, show="headings", height=5
        )
        for c in mtcols:
            self.mem_table.heading(c, text=c)
            self.mem_table.column(c, width=90, anchor="center")
        self.mem_table.pack(fill="x", padx=4)

        # Right: Disk seek path chart
        disk_panel = ctk.CTkFrame(body)
        disk_panel.pack(side="left", fill="both", expand=True, padx=(4, 0))

        ctk.CTkLabel(
            disk_panel,
            text="Disk Scheduling — Seek Path",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(pady=(6, 2))

        self.fig_disk, self.ax_disk = plt.subplots(figsize=(6, 4))
        self.fig_disk.patch.set_facecolor("#1e1e2e")
        self.ax_disk.set_facecolor("#2a2a3e")
        self.canvas_disk = FigureCanvasTkAgg(self.fig_disk, master=disk_panel)
        self.canvas_disk.get_tk_widget().pack(fill="both", expand=True)

        # Disk seek history table
        disk_tbl_frame = ctk.CTkFrame(disk_panel)
        disk_tbl_frame.pack(fill="x", padx=5, pady=(4, 6))

        dtcols = ("#", "Cylinder Visited", "Seek Distance")
        self.disk_table = ttk.Treeview(
            disk_tbl_frame, columns=dtcols, show="headings", height=5
        )
        for c in dtcols:
            self.disk_table.heading(c, text=c)
            self.disk_table.column(c, width=130, anchor="center")
        self.disk_table.pack(fill="x", padx=4)

    def refresh_mem_disk_tab(self):
        """Redraws the Memory & Disk tab charts and tables with live data."""
        def task():
            if not hasattr(self, 'ax_mem') or not hasattr(self, 'ax_disk'):
                return

            # ── Update header labels ─────────────────────────────────────
            self.mem_algo_label.configure(
                text=f"Memory Algorithm: {self.mem_algo.get()}"
            )
            self.disk_algo_label.configure(
                text=f"Disk Algorithm: {self.disk_algo.get()}"
            )
            self.disk_head_label.configure(
                text=f"Disk Head: {self.disk_head}"
            )
            self.total_seek_label.configure(
                text=f"Total Seek: {self.last_disk_seek}"
            )

            # ── Memory bar chart ─────────────────────────────────────────
            self.ax_mem.clear()
            self.ax_mem.set_facecolor("#2a2a3e")

            # Use client device names as labels (or fallback generic names)
            labels = self.client_mem_labels if self.client_mem_labels else ["(none)"]
            total  = self.memory_total  if self.memory_total  else [0]
            free   = self.memory_blocks if self.memory_blocks else [0]
            used   = [max(0, t - f) for t, f in zip(total, free)]

            # Shorten long device names so they fit under bars
            short_labels = [lbl[:10] for lbl in labels]

            n_nodes = len(self.clients)
            self.mem_panel_title.configure(
                text=f"Memory Block Allocation  ({n_nodes} node(s) connected)"
            )

            x = range(len(labels))
            self.ax_mem.bar(x, total, color="#3a3a5e", label="Total RAM", width=0.5)
            self.ax_mem.bar(x, used,  color="#e07b39", label="Used",      width=0.5)
            self.ax_mem.set_xticks(list(x))
            self.ax_mem.set_xticklabels(short_labels, color="white", fontsize=8)
            self.ax_mem.set_ylabel("MB", color="white")
            self.ax_mem.set_title(
                f"RAM per Node  [{self.mem_algo.get()}]  "
                f"| Total pool = {sum(total)} MB",
                color="white"
            )
            self.ax_mem.tick_params(colors="white")
            self.ax_mem.legend(
                loc="upper right", fontsize=8,
                facecolor="#1e1e2e", labelcolor="white"
            )
            self.fig_mem.tight_layout()
            self.canvas_mem.draw()

            # ── Memory block table ───────────────────────────────────────
            self.mem_table.delete(*self.mem_table.get_children())
            for lbl, t, u, f in zip(labels, total, used, free):
                pct    = f"{100 * u // t if t else 0}%"
                ram_gb = round(t / 1024, 1)
                self.mem_table.insert(
                    "", "end",
                    values=(lbl, ram_gb, t, u, f, pct)
                )

            # ── Disk seek-path line chart ─────────────────────────────────
            self.ax_disk.clear()
            self.ax_disk.set_facecolor("#2a2a3e")
            if self.last_disk_order:
                seq  = self.last_disk_order
                head = getattr(self, '_last_dispatch_head', seq[0])
                # Prepend the starting head so the path shows where we came from
                full_seq = [head] + seq
                steps    = list(range(len(full_seq)))
                self.ax_disk.plot(
                    steps, full_seq,
                    marker="o", color="#4fc3f7",
                    linewidth=1.5, markersize=5
                )
                # Annotate each stop
                for i, cyl in enumerate(full_seq):
                    self.ax_disk.annotate(
                        str(cyl),
                        (i, cyl),
                        textcoords="offset points",
                        xytext=(0, 6),
                        ha="center",
                        fontsize=7,
                        color="white"
                    )
                # Mark the starting head with a different colour
                self.ax_disk.plot(0, head, marker="^", color="#ffb74d",
                                  markersize=9, zorder=5, label="Start Head")
                self.ax_disk.set_xlabel("Step  (0 = initial head)", color="white")
                self.ax_disk.set_ylabel("Cylinder", color="white")
                self.ax_disk.set_title(
                    f"Disk Seek Path  [{self.disk_algo.get()}]  "
                    f"Total Seek = {self.last_disk_seek}",
                    color="white"
                )
                self.ax_disk.tick_params(colors="white")
                self.ax_disk.legend(
                    loc="upper right", fontsize=7,
                    facecolor="#1e1e2e", labelcolor="white"
                )
                self.fig_disk.tight_layout()

                # ── Disk seek table ───────────────────────────────────────
                self.disk_table.delete(*self.disk_table.get_children())
                # seq[0] is the first cylinder visited AFTER the initial head
                # We stored the head position before it was updated in dispatch
                prev_cyl = self._last_dispatch_head
                for i, cyl in enumerate(seq):
                    dist = abs(cyl - prev_cyl)
                    self.disk_table.insert(
                        "", "end",
                        values=(i + 1, cyl, dist)
                    )
                    prev_cyl = cyl
            else:
                self.ax_disk.set_title(
                    "Waiting for first disk request…",
                    color="white"
                )
            self.canvas_disk.draw()

        self.ui(task)


root = ctk.CTk()
app = CoordinatorApp(root)
root.mainloop()