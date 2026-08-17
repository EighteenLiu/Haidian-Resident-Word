from __future__ import annotations

import os
import queue
import subprocess
import threading
import time
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.file_classifier import classify_files
from src.pipeline import default_word_template, default_xlsx_template, parse_dates_from_main_file, run_pipeline
from src.models import ReportOptions
from src.utils import PROJECT_ROOT


os.environ.setdefault("TMP", str(PROJECT_ROOT / ".runtime" / "tmp"))
os.environ.setdefault("TEMP", str(PROJECT_ROOT / ".runtime" / "tmp"))
Path(os.environ["TMP"]).mkdir(parents=True, exist_ok=True)


class ResidentReportApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title("海淀区农村人居环境报告生成工具")
        self.geometry("980x760")
        self.minsize(900, 680)
        self.source_files: list[Path] = []
        self.word_template = default_word_template()
        self.xlsx_template = default_xlsx_template()
        self.worker_queue: queue.Queue = queue.Queue()
        self.classify_generation = 0
        self.running = False
        self._build_ui()
        self._refresh_template_labels()
        self.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        pad = {"padx": 14, "pady": 8}

        self.upload_frame = ctk.CTkFrame(self)
        self.upload_frame.grid(row=0, column=0, sticky="ew", **pad)
        self.upload_frame.grid_columnconfigure(0, minsize=140)
        self.upload_frame.grid_columnconfigure(1, weight=1)
        self.upload_frame.grid_columnconfigure(2, minsize=112)
        ctk.CTkLabel(self.upload_frame, text="源数据文件", anchor="w").grid(row=0, column=0, sticky="nsew", padx=(10, 4), pady=(10, 4))
        self.source_text = ctk.CTkTextbox(self.upload_frame, height=108)
        self.source_text.grid(row=0, column=1, sticky="ew", padx=4, pady=(10, 4))
        source_buttons = ctk.CTkFrame(self.upload_frame, fg_color="transparent")
        source_buttons.grid(row=0, column=2, sticky="new", padx=(4, 10), pady=(10, 4))
        self.choose_source_btn = ctk.CTkButton(source_buttons, text="选择", command=self.choose_sources, width=96)
        self.choose_source_btn.pack(fill="x", pady=(0, 6))
        self.recognize_btn = ctk.CTkButton(source_buttons, text="识别", command=self.recognize_sources, width=96)
        self.recognize_btn.pack(fill="x", pady=(0, 6))
        self.clear_source_btn = ctk.CTkButton(source_buttons, text="清空", width=96, command=self.clear_sources)
        self.clear_source_btn.pack(fill="x")

        ctk.CTkLabel(self.upload_frame, text="Word 模板", anchor="w").grid(row=1, column=0, sticky="nsew", padx=(10, 4), pady=4)
        self.word_text = ctk.CTkTextbox(self.upload_frame, height=40)
        self.word_text.grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(self.upload_frame, text="选择", command=self.choose_word_template, width=96).grid(row=1, column=2, sticky="new", padx=(4, 10), pady=4)

        ctk.CTkLabel(self.upload_frame, text="xlsx 模板", anchor="w").grid(row=2, column=0, sticky="nsew", padx=(10, 4), pady=(4, 10))
        self.xlsx_text = ctk.CTkTextbox(self.upload_frame, height=40)
        self.xlsx_text.grid(row=2, column=1, sticky="ew", padx=4, pady=(4, 10))
        ctk.CTkButton(self.upload_frame, text="选择", command=self.choose_xlsx_template, width=96).grid(row=2, column=2, sticky="new", padx=(4, 10), pady=(4, 10))

        self.date_frame = ctk.CTkFrame(self)
        self.date_frame.grid(row=1, column=0, sticky="ew", **pad)
        for i in range(10):
            self.date_frame.grid_columnconfigure(i, weight=1)
        self.year_var = ctk.StringVar()
        self.month_var = ctk.StringVar()
        self.start_var = ctk.StringVar()
        self.end_var = ctk.StringVar()
        self.rounds_var = ctk.StringVar(value="2")
        fields = [("报告年份", self.year_var), ("报告月份", self.month_var), ("数据开始日期", self.start_var), ("数据结束日期", self.end_var), ("检查轮次", self.rounds_var)]
        for idx, (label, var) in enumerate(fields):
            ctk.CTkLabel(self.date_frame, text=label).grid(row=0, column=idx * 2, sticky="e", padx=(10, 2), pady=10)
            ctk.CTkEntry(self.date_frame, textvariable=var, width=110).grid(row=0, column=idx * 2 + 1, sticky="ew", padx=(2, 8), pady=10)

        self.output_frame = ctk.CTkFrame(self)
        self.output_frame.grid(row=2, column=0, sticky="ew", **pad)
        self.output_frame.grid_columnconfigure(1, weight=1)
        self.output_dir_var = ctk.StringVar(value=str(PROJECT_ROOT / "output" / time.strftime("%Y%m%d_%H%M%S")))
        self.open_dir_var = ctk.BooleanVar(value=True)
        ctk.CTkLabel(self.output_frame, text="输出目录").grid(row=0, column=0, padx=10, pady=8)
        ctk.CTkEntry(self.output_frame, textvariable=self.output_dir_var).grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(self.output_frame, text="选择", width=80, command=self.choose_output_dir).grid(row=0, column=2, padx=8)
        ctk.CTkCheckBox(self.output_frame, text="生成后打开输出目录", variable=self.open_dir_var).grid(row=0, column=3, padx=10)

        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=3, column=0, sticky="ew", **pad)
        self.generate_btn = ctk.CTkButton(self.control_frame, text="生成报告", command=self.start_generate)
        self.generate_btn.pack(side="left", padx=10, pady=10)
        self.cancel_btn = ctk.CTkButton(self.control_frame, text="取消", state="disabled")
        self.cancel_btn.pack(side="left", padx=8)
        self.progress = ctk.CTkProgressBar(self.control_frame, mode="indeterminate")
        self.progress.pack(side="left", fill="x", expand=True, padx=10)
        self.status_var = ctk.StringVar(value="等待选择文件")
        ctk.CTkLabel(self.control_frame, textvariable=self.status_var).pack(side="right", padx=10)

        self.log_box = ctk.CTkTextbox(self)
        self.log_box.grid(row=4, column=0, sticky="nsew", **pad)

    def _refresh_template_labels(self) -> None:
        self._set_textbox_value(self.word_text, str(self.word_template) if self.word_template else "未找到模板，请手动选择模板文件。")
        self._set_textbox_value(self.xlsx_text, str(self.xlsx_template) if self.xlsx_template else "未找到模板，请手动选择模板文件。")

    @staticmethod
    def _set_textbox_value(textbox: ctk.CTkTextbox, value: str) -> None:
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.insert("end", value)
        textbox.configure(state="disabled")

    def choose_sources(self) -> None:
        paths = filedialog.askopenfilenames(title="选择源数据文件", filetypes=[("Excel files", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")])
        if paths:
            self.source_files = [Path(p) for p in paths]
            self.refresh_source_list()

    def clear_sources(self) -> None:
        self.source_files = []
        self.classify_generation += 1
        self.source_text.delete("1.0", "end")
        self.status_var.set("等待选择文件")
        self.recognize_btn.configure(text="识别", state="normal")

    def refresh_source_list(self) -> None:
        self.classify_generation += 1
        self.source_text.delete("1.0", "end")
        for path in self.source_files:
            self.source_text.insert("end", f"{path.name} - 等待识别\n")
        self.status_var.set("已选择源文件，点击识别")
        self.recognize_btn.configure(text="识别", state="normal")

    def recognize_sources(self) -> None:
        if self.running:
            return
        if not self.source_files:
            messagebox.showwarning("缺少文件", "请先选择源数据文件。")
            return
        self.classify_generation += 1
        generation = self.classify_generation
        self.status_var.set("正在识别源文件...")
        self.recognize_btn.configure(text="正在识别", state="disabled")
        self.choose_source_btn.configure(state="disabled")
        thread = threading.Thread(target=self._classify_worker, args=(generation, list(self.source_files)), daemon=True)
        thread.start()

    def _classify_worker(self, generation: int, paths: list[Path]) -> None:
        try:
            classified = classify_files(paths)
            parsed_options = None
            main = next((item for item in classified if item.file_type.value == "主数据"), None)
            if main:
                parsed_options = parse_dates_from_main_file(main.path, main.sheet_name)
            self.worker_queue.put(("classified", (generation, classified, parsed_options)))
        except Exception as exc:
            self.worker_queue.put(("classify_error", (generation, str(exc))))

    def _apply_classified_sources(self, generation: int, classified, parsed_options) -> None:
        if generation != self.classify_generation:
            return
        self.source_text.delete("1.0", "end")
        for item in classified:
            self.source_text.insert("end", f"{item.file_type.value} - {item.path.name} - {item.reason}\n")
        if parsed_options:
            try:
                self.year_var.set(str(parsed_options.report_year))
                self.month_var.set(str(parsed_options.report_month))
                self.start_var.set(parsed_options.start_date.isoformat() if parsed_options.start_date else "")
                self.end_var.set(parsed_options.end_date.isoformat() if parsed_options.end_date else "")
            except Exception as exc:
                self.log(f"日期解析失败：{exc}")
        if not self.running:
            self.choose_source_btn.configure(state="normal")
            self.recognize_btn.configure(text="识别完成", state="normal")
        self.status_var.set("文件识别完成")

    def choose_word_template(self) -> None:
        path = filedialog.askopenfilename(title="选择 Word 模板", filetypes=[("Word files", "*.docx"), ("All files", "*.*")])
        if path:
            self.word_template = Path(path)
            self._refresh_template_labels()

    def choose_xlsx_template(self) -> None:
        path = filedialog.askopenfilename(title="选择 xlsx 模板", filetypes=[("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")])
        if path:
            self.xlsx_template = Path(path)
            self._refresh_template_labels()

    def choose_output_dir(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir_var.set(path)

    def start_generate(self) -> None:
        if self.running:
            return
        try:
            options = ReportOptions(
                int(self.year_var.get()),
                int(self.month_var.get()),
                date.fromisoformat(self.start_var.get()) if self.start_var.get() else None,
                date.fromisoformat(self.end_var.get()) if self.end_var.get() else None,
                int(self.rounds_var.get() or "2"),
            )
        except Exception as exc:
            messagebox.showerror("输入错误", f"日期或轮次填写不正确：{exc}")
            return
        self.running = True
        self.generate_btn.configure(state="disabled")
        self.choose_source_btn.configure(state="disabled")
        self.recognize_btn.configure(state="disabled")
        self.clear_source_btn.configure(state="disabled")
        self.progress.start()
        self.status_var.set("正在生成...")
        thread = threading.Thread(target=self._worker, args=(options,), daemon=True)
        thread.start()

    def _worker(self, options: ReportOptions) -> None:
        try:
            result = run_pipeline(
                self.source_files,
                self.word_template,
                self.xlsx_template,
                options,
                Path(self.output_dir_var.get()),
                progress=lambda msg: self.worker_queue.put(("log", msg)),
            )
            self.worker_queue.put(("done", result))
        except Exception as exc:
            self.worker_queue.put(("error", str(exc)))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.worker_queue.get_nowait()
                if kind == "log":
                    self.log(payload)
                    self.status_var.set(payload)
                elif kind == "done":
                    self._finish()
                    self.log(f"生成完成\n用时：{payload.elapsed_seconds:.2f} 秒\n输出目录：{payload.output_dir}")
                    if self.open_dir_var.get():
                        subprocess.Popen(["explorer", str(payload.output_dir)])
                elif kind == "error":
                    self._finish()
                    self.status_var.set(f"生成失败：{payload}")
                    self.log(f"生成失败：{payload}")
                    messagebox.showerror("生成失败", payload)
                elif kind == "classified":
                    generation, classified, parsed_options = payload
                    self._apply_classified_sources(generation, classified, parsed_options)
                elif kind == "classify_error":
                    generation, message = payload
                    if generation == self.classify_generation:
                        if not self.running:
                            self.choose_source_btn.configure(state="normal")
                            self.recognize_btn.configure(text="识别", state="normal")
                        self.status_var.set(f"文件识别失败：{message}")
                        self.log(f"文件识别失败：{message}")
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _finish(self) -> None:
        self.running = False
        self.progress.stop()
        self.generate_btn.configure(state="normal")
        self.choose_source_btn.configure(state="normal")
        self.recognize_btn.configure(state="normal")
        self.clear_source_btn.configure(state="normal")

    def log(self, text: str) -> None:
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")


if __name__ == "__main__":
    ResidentReportApp().mainloop()
