import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import socket
import threading
import json
import time
import random
from collections import deque
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

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

        self.lock = threading.Lock()

        self.build_ui()
        self.start_server()

        threading.Thread(target=self.scheduler_loop, daemon=True).start()

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

        self.tab1 = self.tabs.tab("Control")
        self.tab2 = self.tabs.tab("Devices")
        self.tab3 = self.tabs.tab("Analytics")
        self.tab4 = self.tabs.tab("Chat")

        self.build_tab1()
        self.build_tab2()
        self.build_tab3()
        self.build_tab4()

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

        mid = ctk.CTkFrame(self.tab3)
        mid.pack(fill="both", expand=True, padx=10, pady=5)

        left = ctk.CTkFrame(mid)
        left.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        right = ctk.CTkFrame(mid)
        right.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.fig, self.ax = plt.subplots(figsize=(8, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=left)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        hcols = ("Task", "Worker", "Wait", "TAT")
        self.history_tree = ttk.Treeview(
            right,
            columns=hcols,
            show="headings",
            height=10
        )

        for c in hcols:
            self.history_tree.heading(c, text=c)
            self.history_tree.column(c, width=110, anchor="center")

        self.history_tree.pack(fill="both", expand=True, padx=5, pady=5)

        self.log = ctk.CTkTextbox(right, height=220)
        self.log.pack(fill="both", expand=True, padx=5, pady=5)
    
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

        self.send_btn = ctk.CTkButton(
            bottom,
            text="Send",
            width=120,
            command=self.send_chat_from_coordinator
        )
        self.send_btn.pack(side="right")

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
                        
    def add_client(self, sock, ip, msg):
        with self.lock:
            self.clients.append({
                "socket": sock,
                "device": msg["device"],
                "ip": ip,
                "cpu": msg["cpu"],
                "ram": msg["ram"],
                "disk": msg["disk"],
                "used_cpu": 0,
                "used_ram": 0,
                "used_disk": 0,
                "busy": False,
                "load": 0
            })

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
        task = {
            "name": msg["task"],
            "parent": msg["parent"],
            "duration": msg["duration"],
            "priority": random.randint(1, 5),
            "arrival": time.time()
        }

        with self.lock:
            self.pending_tasks.append(task)

        self.ui(self.refresh_queue)

        def add_row():
            self.process_tree.insert(
                "",
                "end",
                values=(
                    task["parent"],
                    task["name"],
                    task["priority"],
                    "-",
                    "Queued"
                )
            )
        self.ui(add_row)

    # ------------------------------------------------ Refresh lists

    def refresh_sessions(self):
        self.session_list.delete(0, "end")
        for s in self.sessions:
            self.session_list.insert("end", s)

    def refresh_queue(self):
        self.queue_list.delete(0, "end")
        for t in self.pending_tasks:
            self.queue_list.insert(
                "end",
                f'{t["name"]} ({t["duration"]}s)'
            )
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

    def scheduler_loop(self):
        while True:
            try:
                self.dispatch_tasks()
                self.ui(self.update_stats)
            except:
                pass
            time.sleep(0.5)

    def choose_task(self):
        if not self.pending_tasks:
            return None

        algo = self.cpu_algo.get()

        if algo == "FCFS":
            return self.pending_tasks.pop(0)

        if algo == "SJF":
            idx = min(
                range(len(self.pending_tasks)),
                key=lambda i: self.pending_tasks[i]["duration"]
            )
            return self.pending_tasks.pop(idx)

        if algo == "PRIORITY":
            idx = min(
                range(len(self.pending_tasks)),
                key=lambda i: self.pending_tasks[i]["priority"]
            )
            return self.pending_tasks.pop(idx)

        if algo == "RR":
            self.rr_index %= len(self.pending_tasks)
            return self.pending_tasks.pop(self.rr_index)

        return self.pending_tasks.pop(0)

    def choose_worker(self):
        free = [c for c in self.clients if not c["busy"]]
        if not free:
            return None

        return min(
            free,
            key=lambda x: (x["load"], x["used_cpu"])
        )

    def dispatch_tasks(self):
        while True:
            with self.lock:
                worker = self.choose_worker()
                if not worker or not self.pending_tasks:
                    return

                task = self.choose_task()

                worker["busy"] = True
                worker["load"] += 1
                worker["used_cpu"] = random.randint(45, 95)
                worker["used_ram"] = min(worker["ram"], random.randint(1, worker["ram"]))
                worker["used_disk"] = min(worker["disk"], random.randint(5, worker["disk"]))

            try:
                worker["socket"].send(json.dumps({
                    "type": "run_task",
                    "task": task["name"],
                    "duration": task["duration"]
                }).encode())
            except:
                with self.lock:
                    worker["busy"] = False
                return

            self.running_tasks.append(
                f'{task["name"]} -> {worker["device"]}'
            )

            self.mark_running(task, worker["device"])

            self.ui(self.refresh_queue)
            self.ui(self.refresh_running)
            self.ui(self.update_table)

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

        now = time.time()

        with self.lock:
            for c in self.clients:
                if c["device"] == dev:
                    c["busy"] = False
                    c["used_cpu"] = 0
                    c["used_ram"] = 0
                    c["used_disk"] = 0

            self.running_tasks = [
                x for x in self.running_tasks
                if not (task_name in x and dev in x)
            ]

            self.completed += 1

        wait = round(random.uniform(0.5, 3.0), 2)
        tat = round(wait + random.uniform(2.0, 6.0), 2)

        self.total_wait += wait
        self.total_tat += tat

        self.completed_tasks.append(f"{task_name} by {dev}")
        self.gantt.append((task_name, random.randint(2, 5)))

        def update_rows():
            for row in self.process_tree.get_children():
                vals = self.process_tree.item(row, "values")
                if vals[1] == task_name and vals[3] == dev and vals[4] == "Running":
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

        self.write_log(f"{task_name} completed by {dev}")

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


root = ctk.CTk()
app = CoordinatorApp(root)
root.mainloop()