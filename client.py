import customtkinter as ctk
import socket
import json
import platform
import random
import threading
import time

PORT = 5000

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed Client Node")
        self.root.geometry("1100x920")

        self.sock = None
        self.connected = False
        self.worker_busy = False
        self.sessions = {}

        self.device_name = platform.node()
        self.cpu = random.randint(2, 8)
        self.ram = random.randint(4, 16)
        self.disk = random.randint(64, 512)

        self.build_ui()

    # ------------------------------------------------ UI

    def build_ui(self):
        title = ctk.CTkLabel(
            self.root,
            text="Distributed Client Node",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=14)

        self.tabs = ctk.CTkTabview(self.root)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=8)

        self.tabs.add("Dashboard")
        self.tabs.add("Chat")

        self.dashboard_scroll = ctk.CTkScrollableFrame(self.tabs.tab("Dashboard"))
        self.dashboard_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        self.tab1 = self.dashboard_scroll
        self.tab2 = self.tabs.tab("Chat")

        self.build_dashboard()
        self.build_chat_tab()

    def build_dashboard(self):
        self.build_connect(self.tab1)
        self.build_resources(self.tab1)
        self.build_jobs(self.tab1)
        self.build_sessions(self.tab1)
        self.build_process(self.tab1)
        self.build_logs(self.tab1)

    
    def build_chat_tab(self):
        frame = ctk.CTkFrame(self.tab2)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            frame,
            text="Group Chat",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=8)

        self.chat_box = ctk.CTkTextbox(frame)
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.chat_box.configure(state="disabled")

        bottom = ctk.CTkFrame(frame)
        bottom.pack(fill="x", padx=10, pady=(0,10))

        self.chat_entry = ctk.CTkEntry(
            bottom,
            placeholder_text="Type message..."
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0,10))
        self.chat_entry.bind("<Return>", lambda e: self.send_chat())

        self.chat_btn = ctk.CTkButton(
            bottom,
            text="Send",
            width=110,
            command=self.send_chat
        )
        self.chat_btn.pack(side="right")

    def build_connect(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(frame, text="Coordinator IP").grid(
            row=0, column=0, padx=10, pady=10
        )

        self.ip_entry = ctk.CTkEntry(frame, width=220)
        self.ip_entry.grid(row=0, column=1, padx=10)

        self.connect_btn = ctk.CTkButton(
            frame,
            text="Connect",
            width=120,
            command=self.connect_server
        )
        self.connect_btn.grid(row=0, column=2, padx=10)

        self.conn_label = ctk.CTkLabel(
            frame,
            text="Disconnected",
            text_color="red"
        )
        self.conn_label.grid(row=0, column=3, padx=10)

    def build_resources(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=12, pady=8)

        txt = (
            f"Device: {self.device_name}\n"
            f"CPU: {self.cpu} Cores\n"
            f"RAM: {self.ram} GB\n"
            f"Disk: {self.disk} GB"
        )

        ctk.CTkLabel(
            frame,
            text=txt,
            justify="left",
            anchor="w"
        ).pack(fill="x", padx=15, pady=12)

    def build_jobs(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            frame,
            text="Jobs",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, columnspan=3, pady=10)

        jobs = ["Game", "Compile", "Backup", "Analysis"]

        for i, job in enumerate(jobs, start=1):
            ctk.CTkLabel(frame, text=job, width=120).grid(
                row=i, column=0, padx=10, pady=6
            )

            ctk.CTkButton(
                frame,
                text="Start",
                width=100,
                command=lambda j=job: self.start_job(j)
            ).grid(row=i, column=1, padx=10)

            ctk.CTkButton(
                frame,
                text="Stop",
                width=100,
                fg_color="#b22222",
                hover_color="#8b1a1a",
                command=lambda j=job: self.stop_job(j)
            ).grid(row=i, column=2, padx=10)

        ctk.CTkButton(
            frame,
            text="Stop All",
            width=220,
            fg_color="#d2691e",
            hover_color="#a0522d",
            command=self.stop_all
        ).grid(row=6, column=0, columnspan=3, pady=12)

    def build_sessions(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            frame,
            text="Running Jobs",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(10, 6))

        self.session_box = ctk.CTkTextbox(frame, height=120)
        self.session_box.pack(fill="x", padx=10, pady=(0, 10))
        self.session_box.configure(state="disabled")

    def build_process(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            frame,
            text="Current Process",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(10, 6))

        self.task_label = ctk.CTkLabel(frame, text="Idle")
        self.task_label.pack(pady=5)

        self.progress = ctk.CTkProgressBar(frame, width=700)
        self.progress.pack(padx=12, pady=10)
        self.progress.set(0)

    def build_logs(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=12, pady=8)

        ctk.CTkLabel(
            frame,
            text="Logs",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(10, 6))

        self.output = ctk.CTkTextbox(frame, height=140)
        self.output.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ------------------------------------------------ Safe UI

    def ui(self, fn):
        self.root.after(0, fn)

    def log(self, msg):
        def task():
            now = time.strftime("%H:%M:%S")
            self.output.insert("end", f"[{now}] {msg}\n")
            self.output.see("end")
        self.ui(task)

    def send_chat(self):
        if not self.connected:
            self.log("Connect first")
            return
        text = self.chat_entry.get().strip()

        if text == "":
            return

        sender_name = f"Client:{self.device_name}"

        self.send_json({
            "type": "chat",
            "sender": sender_name,
            "message": text
        })

        self.chat_entry.delete(0, "end")

    def display_chat(self, sender, message):
        def task():
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"[{sender}] {message}\n")
            self.chat_box.see("end")
            self.chat_box.configure(state="disabled")

        self.ui(task)

    # ------------------------------------------------ Connection

    def connect_server(self):
        ip = self.ip_entry.get().strip()

        if ip == "":
            self.log("Enter coordinator IP")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((ip, PORT))

            self.connected = True

            self.send_json({
                "type": "join",
                "device": self.device_name,
                "cpu": self.cpu,
                "ram": self.ram,
                "disk": self.disk
            })

            self.connect_btn.configure(state="disabled")
            self.conn_label.configure(
                text="Connected",
                text_color="lightgreen"
            )

            self.log("Connected to coordinator")

            threading.Thread(
                target=self.listen_server,
                daemon=True
            ).start()

        except Exception as e:
            self.connected = False
            self.log(f"Connection failed: {e}")

    def disconnect_ui(self):
        self.connected = False
        self.worker_busy = False

        self.connect_btn.configure(state="normal")
        self.conn_label.configure(
            text="Disconnected",
            text_color="red"
        )

    # ------------------------------------------------ Jobs

    def start_job(self, name):
        if not self.connected:
            self.log("Connect first")
            return

        if self.sessions.get(name, False):
            self.log(f"{name} already running")
            return

        self.sessions[name] = True
        self.refresh_sessions()

        self.send_json({
            "type": "session_start",
            "app": name,
            "device": self.device_name
        })

        self.log(f"{name} started")

        threading.Thread(
            target=self.job_loop,
            args=(name,),
            daemon=True
        ).start()

    def stop_job(self, name):
        if not self.sessions.get(name, False):
            return

        self.sessions[name] = False
        self.refresh_sessions()

        self.send_json({
            "type": "session_stop",
            "app": name,
            "device": self.device_name
        })

        self.log(f"{name} stopped")

    def stop_all(self):
        for name in list(self.sessions.keys()):
            if self.sessions[name]:
                self.sessions[name] = False

                self.send_json({
                    "type": "session_stop",
                    "app": name,
                    "device": self.device_name
                })

        self.refresh_sessions()
        self.log("All jobs stopped")

    def refresh_sessions(self):
        def task():
            self.session_box.configure(state="normal")
            self.session_box.delete("1.0", "end")

            for name in self.sessions:
                if self.sessions[name]:
                    self.session_box.insert("end", f"{name} Running\n")

            self.session_box.configure(state="disabled")

        self.ui(task)

    def job_loop(self, app):
        process_map = {
            "Game": ["Render", "Physics", "Audio", "Network"],
            "Compile": ["Parse", "Compile", "Link", "Build"],
            "Backup": ["Read Disk", "Compress", "Write Disk"],
            "Analysis": ["Load Data", "Compute", "Save Result"]
        }

        while self.sessions.get(app, False) and self.connected:
            proc = random.choice(process_map[app])

            self.send_json({
                "type": "task_request",
                "task": proc,
                "parent": app,
                "duration": random.randint(3, 7)
            })

            self.log(f"{app} generated process: {proc}")
            time.sleep(random.randint(2, 4))

    # ------------------------------------------------ Server Listen

    def listen_server(self):
        while self.connected:
            try:
                data = self.sock.recv(4096).decode()

                if not data:
                    break

                msg = json.loads(data)

                if msg["type"] == "run_task":
                    if self.worker_busy:
                        continue

                    self.worker_busy = True

                    threading.Thread(
                        target=self.run_task,
                        args=(msg["task"], msg["duration"]),
                        daemon=True
                    ).start()

                elif msg["type"] == "chat":
                    self.display_chat(
                        msg.get("sender", "Unknown"),
                        msg.get("message", "")
                    )

            except:
                break

        self.ui(self.disconnect_ui)
        self.log("Disconnected from coordinator")

    # ------------------------------------------------ Execute Task

    def run_task(self, task, duration):
        self.ui(lambda: self.task_label.configure(text=f"Running: {task}"))
        self.ui(lambda: self.progress.set(0))

        self.log(f"Started process: {task}")

        steps = max(1, duration * 10)

        for i in range(steps):
            time.sleep(duration / steps)
            value = (i + 1) / steps
            self.ui(lambda v=value: self.progress.set(v))

        self.ui(lambda: self.task_label.configure(text="Idle"))
        self.ui(lambda: self.progress.set(0))

        self.log(f"Completed process: {task}")

        self.send_json({
            "type": "task_done",
            "device": self.device_name,
            "task": task
        })

        self.worker_busy = False

    # ------------------------------------------------ Send

    def send_json(self, obj):
        try:
            if self.sock and self.connected:
                self.sock.send(json.dumps(obj).encode())
        except:
            pass


root = ctk.CTk()
app = ClientApp(root)
root.mainloop()