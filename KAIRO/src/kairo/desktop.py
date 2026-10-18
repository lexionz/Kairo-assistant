import asyncio
import json
import math
import queue
import threading
import tkinter as tk
from tkinter import ttk


class Desktop:
    colors = {"idle": "#bac8c5", "listening": "#92e0c4", "thinking": "#e5e4d8", "acting": "#e5bd79", "permission": "#edc879", "speaking": "#9ccce7", "success": "#b1ddb6", "error": "#e69380", "interrupted": "#959ba3"}

    def __init__(self, application, smoke=False):
        self.app = application
        self.smoke = smoke
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self.inbox = queue.Queue()
        self.app.events.subscribe(self.inbox.put)
        self.root = tk.Tk()
        self.root.title("KAIRO")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#020304")
        try:
            self.root.attributes("-transparentcolor", "#020304")
        except tk.TclError:
            pass
        self.root.geometry(f"240x114+{self.root.winfo_screenwidth() // 2 - 120}+8")
        self.canvas = tk.Canvas(self.root, width=240, height=114, bg="#020304", highlightthickness=0)
        self.canvas.pack()
        self.state = "idle"
        self.text = "KAIRO · mic off"
        self.level = 0
        self.frame = 0
        self.review = None
        self.panel = None
        self.last_result = {}
        self.canvas.bind("<ButtonPress-1>", self.press)
        self.canvas.bind("<ButtonRelease-1>", lambda _: self.loop.call_soon_threadsafe(self.app.release))
        self.canvas.bind("<Button-3>", lambda _: self.show_panel())
        self.root.bind("<Escape>", lambda _: self.submit(self.app.cancel()))
        self.menu = tk.Menu(self.root, tearoff=False)
        self.menu.add_command(label="Settings, research & activity", command=self.show_panel)
        self.menu.add_command(label="Stop", command=lambda: self.submit(self.app.cancel()))
        self.menu.add_command(label="Quit KAIRO", command=self.close)
        self.canvas.bind("<Button-2>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self.root.after(30, self.tick)

    def submit(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop)

    def press(self, event):
        if self.state == "permission":
            self.show_panel()
        elif self.state in {"idle", "success", "error", "interrupted"}:
            self.submit(self.app.request())
        else:
            self.submit(self.app.cancel())

    def show_panel(self):
        if self.panel and self.panel.winfo_exists():
            self.panel.lift()
            self.render_review()
            return
        self.panel = tk.Toplevel(self.root)
        self.panel.title("KAIRO · controls")
        self.panel.geometry("760x690")
        self.panel.configure(bg="#101718")
        self.panel.bind("<Escape>", lambda _: self.submit(self.app.cancel()))
        tabs = ttk.Notebook(self.panel)
        tabs.pack(fill="both", expand=True, padx=14, pady=14)
        task, settings, activity = [ttk.Frame(tabs, padding=12) for _ in range(3)]
        for label, frame in zip(("Task & review", "Settings & tools", "Memory & evidence"), (task, settings, activity)):
            tabs.add(frame, text=label)
        ttk.Label(task, text="Hold the core to speak. Release to finish. Click while busy or press Esc to stop.").pack(anchor="w")
        entry = ttk.Entry(task)
        entry.pack(fill="x", pady=10)
        ttk.Button(task, text="Run written request", command=lambda: self.submit(self.app.request(entry.get()))).pack(anchor="w")
        self.review_text = tk.Text(task, wrap="word", height=22, bg="#0b1112", fg="#d6e0dc", insertbackground="white")
        self.review_text.pack(fill="both", expand=True, pady=10)
        decisions = ttk.Frame(task)
        decisions.pack(fill="x")
        self.allow = ttk.Button(decisions, text="Approve exactly this action", command=lambda: self.decide(True))
        self.allow.pack(side="left")
        ttk.Button(decisions, text="Deny", command=lambda: self.decide(False)).pack(side="left", padx=8)
        ttk.Button(decisions, text="Stop", command=lambda: self.submit(self.app.cancel())).pack(side="right")
        ttk.Label(settings, text="Model endpoint (HTTPS, or explicit loopback for local inference)").pack(anchor="w")
        endpoint = ttk.Entry(settings)
        endpoint.insert(0, self.app.config["brain"].get("endpoint", ""))
        endpoint.pack(fill="x", pady=8)
        ttk.Label(settings, text="Model ID").pack(anchor="w")
        model = ttk.Entry(settings)
        model.insert(0, self.app.config["brain"].get("model", ""))
        model.pack(fill="x", pady=8)
        ttk.Button(settings, text="Save provider", command=lambda: self.submit(self.app.save_settings(endpoint.get(), model.get(), self.app.config["brain"].get("provider", "compatible")))).pack(anchor="w")
        ttk.Label(settings, wraplength=650, text="For a cloud provider set KAIRO_API_KEY in the launch environment. Keys are never shown or stored here. Microphone input uses the Windows default device. Wake-word listening is off.").pack(anchor="w", pady=16)
        ttk.Label(settings, wraplength=650, text="Project and command allowlists are owner-managed in " + str(self.app.config_file)).pack(anchor="w", pady=8)
        ttk.Button(settings, text="Connect configured MCP tools", command=lambda: self.submit(self.app.connect_mcp())).pack(anchor="w")
        ttk.Button(settings, text="Quit KAIRO", command=self.close).pack(anchor="w", pady=18)
        self.activity_text = tk.Text(activity, wrap="word", bg="#0b1112", fg="#d6e0dc")
        self.activity_text.pack(fill="both", expand=True)
        ttk.Button(activity, text="Refresh", command=lambda: self.submit(self.app.snapshot())).pack(anchor="w")
        self.notice = ttk.Label(self.panel, text="Microphone is off except while explicitly listening.", wraplength=730)
        self.notice.pack(fill="x", padx=14, pady=8)
        self.render_review()
        self.submit(self.app.snapshot())

    def render_review(self):
        if not self.panel or not self.panel.winfo_exists():
            return
        self.review_text.delete("1.0", "end")
        self.review_text.insert("end", json.dumps(self.review or self.last_result, ensure_ascii=False, indent=2))
        self.allow.configure(state="normal" if self.review else "disabled")

    def decide(self, allowed):
        if self.review:
            review = self.review
            self.loop.call_soon_threadsafe(self.app.authority.decide, review["token"], review["task"], allowed)

    def tick(self):
        while not self.inbox.empty():
            event = self.inbox.get_nowait()
            if event.kind == "state":
                self.state = event.payload["state"]
                self.text = event.payload.get("text", self.state)
                if self.state in {"success", "interrupted"}:
                    state = self.state
                    self.root.after(2500, lambda s=state: self.collapse(s))
            elif event.kind == "audio":
                self.level = event.payload["level"] / 100
            elif event.kind == "approval":
                self.review = event.payload
                self.show_panel()
            elif event.kind == "approval_closed":
                self.review = None
                self.render_review()
            elif event.kind == "result":
                self.last_result = event.payload
                self.render_review()
            elif event.kind == "snapshot" and self.panel and self.panel.winfo_exists():
                self.activity_text.delete("1.0", "end")
                self.activity_text.insert("end", json.dumps({**event.payload, "current_research": self.last_result}, ensure_ascii=False, indent=2))
            elif event.kind == "notice" and self.panel and self.panel.winfo_exists():
                self.notice.configure(text=event.payload["text"])
        self.draw()
        self.root.after(40, self.tick)

    def collapse(self, expected):
        if self.state == expected:
            self.state = "idle"
            self.text = "KAIRO · mic off"

    def draw(self):
        self.canvas.delete("all")
        self.frame += 1
        color = self.colors[self.state]
        active = self.state in {"thinking", "acting", "speaking"}
        radius = 25 + (2 * math.sin(self.frame / 6) if active else 0)
        self.canvas.create_oval(120-radius, 40-radius, 120+radius, 40+radius, fill="#0b1012", outline="#384749")
        phase = self.frame * 5 if active else 25
        self.canvas.create_arc(87, 7, 153, 73, start=phase, extent=235, style="arc", outline=color, width=2)
        self.canvas.create_line(111, 28, 111, 52, 122, 41, 132, 52, fill=color, width=2)
        self.canvas.create_line(122, 41, 132, 28, fill=color, width=2)
        if self.state == "listening":
            for i in range(11):
                height = 2 + self.level * (8 + 6 * math.sin(i * 2 + self.frame))
                self.canvas.create_line(85 + i*7, 86-height, 85+i*7, 86+height, fill=color, width=2)
        else:
            self.canvas.create_text(120, 86, text=self.text[:36], fill=color, font=("Segoe UI", 9))
        self.canvas.create_text(120, 104, text="MIC ON" if self.state == "listening" else "hold to talk · right-click controls", fill="#e89a83" if self.state == "listening" else "#7d9994", font=("Segoe UI", 8))

    def close(self):
        self.submit(self.app.cancel())
        self.loop.call_soon_threadsafe(self.app.mcp_stop.set)
        self.root.after(400, self.root.destroy)

    def run(self):
        self.root.mainloop()
