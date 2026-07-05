import requests
import sys
import configparser
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
from openai import OpenAI
import threading


def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_app_dir()


def load_config():
    config = configparser.ConfigParser()
    config_path = os.path.join(APP_DIR, 'config.ini')
    config.read(config_path, encoding='utf-8')
    return config


config = load_config()

API_BASE_URL = "http://127.0.0.1:5031"
ACCESS_TOKEN = config.get('base', 'token', fallback='')
MESSAGES_NUM = config.getint('base', 'messages_num', fallback=10)

AI_BASE_URL = config.get('ai', 'base_url', fallback='http://127.0.0.1:5031')
AI_API_KEY = config.get('ai', 'api_key', fallback='')
AI_MODEL = config.get('ai', 'model_name', fallback='gpt-4o-mini')
ASK_PROMPT = config.get('ai', 'ask_prompt', fallback='请根据以下聊天记录回答问题：')
IMPORTANT_PROMPT = config.get('ai', 'important_prompt', fallback='重要事项：')
AGENCY_PROMPT = config.get('ai', 'agency_prompt', fallback='待办事项：')

def get_api_params():
    """获取API请求参数（包含token）"""
    params = {}
    if ACCESS_TOKEN:
        params['access_token'] = ACCESS_TOKEN
    return params

def get_sessions(keyword="", limit=100):
    """获取会话列表"""
    url = f"{API_BASE_URL}/api/v1/sessions"
    params = {
        "keyword": keyword,
        "limit": limit
    }
    params.update(get_api_params())
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            return data.get("sessions", [])
        else:
            return []
    except requests.exceptions.RequestException as e:
        print(f"获取会话失败: {e}")
        return []

def get_group_sessions():
    """获取所有群聊会话"""
    sessions = get_sessions(limit=1000)
    # 群聊的 username 通常以 @chatroom 结尾
    groups = [s for s in sessions if s.get('username', '').endswith('@chatroom')]
    return groups

def get_messages(talker, limit=100):
    """获取指定会话的消息"""
    url = f"{API_BASE_URL}/api/v1/messages"
    params = {
        "talker": talker,
        "limit": limit
    }
    params.update(get_api_params())
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            return data.get("messages", [])
        else:
            return []
    except requests.exceptions.RequestException as e:
        print(f"获取消息失败: {e}")
        return []

def format_messages_for_ai(messages, group_name=""):
    """将消息格式化为适合AI处理的文本"""
    formatted = []
    if group_name:
        formatted.append(f"【群聊：{group_name}】\n")
    
    for msg in messages:
        create_time = msg.get("createTime", 0)
        time_str = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S") if create_time else "未知时间"
        
        is_send = msg.get("isSend", 0)
        sender = "我" if is_send else msg.get("senderUsername", "未知")
        
        content = msg.get("parsedContent", msg.get("content", ""))
        media_type = msg.get("mediaType", "")
        
        if media_type == "image":
            content = "[图片]"
        elif media_type == "voice":
            content = "[语音]"
        elif media_type == "video":
            content = "[视频]"
        elif media_type == "emoji":
            content = "[表情]"
        
        formatted.append(f"[{time_str}] {sender}: {content}")
    
    return "\n".join(formatted)

def call_ai(prompt, messages_text):
    """调用AI接口"""
    try:
        client = OpenAI(
            api_key=AI_API_KEY,
            base_url=AI_BASE_URL
        )
        
        full_prompt = f"{prompt}\n\n{messages_text}"
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个专业的聊天记录分析助手，擅长从聊天记录中提取重要信息。"},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"AI调用失败: {e}"

def save_to_file(content, filename):
    filepath = os.path.join(APP_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return filepath

BG_COLOR = "#f5f7fa"
CARD_COLOR = "#ffffff"
ACCENT = "#4a90d9"
ACCENT_HOVER = "#357abd"
ACCENT_LIGHT = "#e8f0fe"
TEXT_PRIMARY = "#2c3e50"
TEXT_SECONDARY = "#7f8c8d"
BTN_ASK = "#4a90d9"
BTN_IMPORTANT = "#e67e22"
BTN_AGENCY = "#27ae60"
TAG_BG = "#f0f2f5"
TAG_BG_HOVER = "#e4e8ed"
TAG_BG_SELECTED = "#e8f0fe"
TAG_BORDER = "#dcdfe6"
TAG_BORDER_SELECTED = "#4a90d9"
TAG_FG = "#4a5568"
TAG_FG_SELECTED = "#2b6cb0"


class WeFlowAssistantGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WeFlow 聊天记录智能助手")
        self.root.geometry("880x720")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(True, True)
        self.root.minsize(720, 600)

        self.groups = []
        self.group_vars = []
        self.group_checkbuttons = []
        self.current_result = ""
        self.current_result_type = ""

        self._setup_styles()
        self.setup_ui()
        self.load_groups()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=BG_COLOR)
        style.configure('Card.TFrame', background=CARD_COLOR)
        style.configure('TLabel', background=BG_COLOR, foreground=TEXT_PRIMARY, font=("微软雅黑", 10))
        style.configure('Card.TLabel', background=CARD_COLOR, foreground=TEXT_PRIMARY)
        style.configure('Title.TLabel', background=BG_COLOR, foreground=TEXT_PRIMARY, font=("微软雅黑", 18, "bold"))
        style.configure('Subtitle.TLabel', background=CARD_COLOR, foreground=TEXT_SECONDARY, font=("微软雅黑", 9))
        style.configure('Status.TLabel', background="#e8ecf1", foreground=TEXT_SECONDARY, font=("微软雅黑", 9), padding=(10, 4))
        style.configure('Small.TButton', font=("微软雅黑", 9), padding=(8, 2))

    def _make_card(self, parent, **kw):
        frame = tk.Frame(parent, bg=CARD_COLOR, bd=0, highlightthickness=1,
                         highlightbackground="#e0e0e0", **kw)
        return frame

    def _make_action_btn(self, parent, text, color, command):
        btn = tk.Button(parent, text=text, font=("微软雅黑", 11, "bold"),
                        fg="white", bg=color, activebackground=color,
                        activeforeground="white", bd=0, cursor="hand2",
                        padx=20, pady=8, command=command)
        btn.bind("<Enter>", lambda e, b=btn, c=color: b.config(bg=self._darken(c)))
        btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(bg=c))
        return btn

    @staticmethod
    def _darken(hex_color, factor=0.85):
        hex_color = hex_color.lstrip('#')
        r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

    def setup_ui(self):
        self.status_var = tk.StringVar(value="就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var, font=("微软雅黑", 9),
                              fg=TEXT_SECONDARY, bg="#e8ecf1", anchor=tk.W, padx=10, pady=4)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 0))

        title_label = tk.Label(main_frame, text="WeFlow 聊天记录智能助手",
                               font=("微软雅黑", 16, "bold"), fg=TEXT_PRIMARY, bg=BG_COLOR)
        title_label.pack(anchor=tk.W, pady=(0, 10))

        content_frame = tk.Frame(main_frame, bg=BG_COLOR)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=2, minsize=280)
        content_frame.columnconfigure(1, weight=5, minsize=500)
        content_frame.rowconfigure(0, weight=1)

        left_panel = tk.Frame(content_frame, bg=BG_COLOR)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        group_card = self._make_card(left_panel)
        group_card.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(group_card, bg=CARD_COLOR)
        header.pack(fill=tk.X, padx=14, pady=(10, 0))

        tk.Label(header, text="选择群聊", font=("微软雅黑", 12, "bold"),
                 fg=TEXT_PRIMARY, bg=CARD_COLOR).pack(side=tk.LEFT)

        self.selected_count_label = tk.Label(header, text="", font=("微软雅黑", 9),
                                             fg=ACCENT, bg=CARD_COLOR)
        self.selected_count_label.pack(side=tk.LEFT, padx=(8, 0))

        btn_frame = tk.Frame(header, bg=CARD_COLOR)
        btn_frame.pack(side=tk.RIGHT)

        for txt, cmd in [("全选", self.select_all), ("取消", self.deselect_all), ("刷新", self.load_groups)]:
            b = tk.Button(btn_frame, text=txt, font=("微软雅黑", 9), fg=ACCENT,
                      bg=CARD_COLOR, bd=0, cursor="hand2", padx=6, pady=1,
                      activeforeground=ACCENT_HOVER, activebackground=CARD_COLOR,
                      command=cmd)
            b.pack(side=tk.LEFT, padx=1)
            b.bind("<Enter>", lambda e, btn=b: btn.config(fg=ACCENT_HOVER, font=("微软雅黑", 9, "underline")))
            b.bind("<Leave>", lambda e, btn=b: btn.config(fg=ACCENT, font=("微软雅黑", 9)))

        sep = tk.Frame(group_card, bg="#eef0f4", height=1)
        sep.pack(fill=tk.X, padx=14, pady=(8, 0))

        list_container = tk.Frame(group_card, bg=CARD_COLOR)
        list_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 8))

        self.tag_canvas = tk.Canvas(list_container, bg=CARD_COLOR, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.tag_canvas.yview)
        self.tag_inner_frame = tk.Frame(self.tag_canvas, bg=CARD_COLOR)

        self.tag_inner_frame.bind("<Configure>",
            lambda e: self.tag_canvas.configure(scrollregion=self.tag_canvas.bbox("all")))
        self.tag_canvas.create_window((0, 0), window=self.tag_inner_frame, anchor=tk.NW)
        self.tag_canvas.configure(yscrollcommand=scrollbar.set)

        self.tag_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tag_canvas.bind("<Enter>", lambda e: self.tag_canvas.bind_all("<MouseWheel>",
            lambda ev: self.tag_canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")))
        self.tag_canvas.bind("<Leave>", lambda e: self.tag_canvas.unbind_all("<MouseWheel>"))

        action_card = self._make_card(left_panel)
        action_card.pack(fill=tk.X, pady=(8, 0))

        action_inner = tk.Frame(action_card, bg=CARD_COLOR)
        action_inner.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(action_inner, text="功能操作", font=("微软雅黑", 11, "bold"),
                 fg=TEXT_PRIMARY, bg=CARD_COLOR).pack(anchor=tk.W, pady=(0, 6))

        btn_col = tk.Frame(action_inner, bg=CARD_COLOR)
        btn_col.pack(fill=tk.X)

        self._make_action_btn(btn_col, "智能问答", BTN_ASK, self.do_ask).pack(fill=tk.X, pady=(0, 4))
        self._make_action_btn(btn_col, "记录重要事项", BTN_IMPORTANT, self.do_important).pack(fill=tk.X, pady=(0, 4))
        self._make_action_btn(btn_col, "记录待办事项", BTN_AGENCY, self.do_agency).pack(fill=tk.X)

        right_panel = tk.Frame(content_frame, bg=BG_COLOR)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right_panel.rowconfigure(0, weight=2)
        right_panel.rowconfigure(1, weight=3)
        right_panel.columnconfigure(0, weight=1)

        preview_card = self._make_card(right_panel)
        preview_card.grid(row=0, column=0, sticky="nsew", pady=(0, 6))

        preview_header = tk.Frame(preview_card, bg=CARD_COLOR)
        preview_header.pack(fill=tk.X, padx=14, pady=(10, 0))

        self.preview_title = tk.Label(preview_header, text="消息预览",
                                      font=("微软雅黑", 12, "bold"), fg=TEXT_PRIMARY, bg=CARD_COLOR)
        self.preview_title.pack(side=tk.LEFT)

        self.preview_hint = tk.Label(preview_header, text="选择群聊后展示近50条消息",
                                     font=("微软雅黑", 9), fg=TEXT_SECONDARY, bg=CARD_COLOR)
        self.preview_hint.pack(side=tk.RIGHT)

        self.preview_text = scrolledtext.ScrolledText(preview_card, font=("微软雅黑", 9),
                                                      bg="#f8f9fb", fg=TEXT_PRIMARY,
                                                      bd=0, padx=14, pady=10,
                                                      wrap=tk.WORD, state=tk.DISABLED,
                                                      insertbackground=TEXT_PRIMARY,
                                                      spacing1=1, spacing3=1,
                                                      selectbackground=ACCENT_LIGHT)
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        self.preview_text.tag_configure("group_name",
            foreground="#ffffff", font=("微软雅黑", 9, "bold"),
            background=ACCENT, relief=tk.FLAT, borderwidth=0,
            lmargin1=20, lmargin2=20, rmargin=20,
            spacing1=6, spacing3=6)
        self.preview_text.tag_configure("time",
            foreground="#a0aec0", font=("微软雅黑", 8),
            lmargin1=10)
        self.preview_text.tag_configure("sender_me",
            foreground=ACCENT, font=("微软雅黑", 9, "bold"),
            lmargin1=10)
        self.preview_text.tag_configure("sender_other",
            foreground="#e67e22", font=("微软雅黑", 9, "bold"),
            lmargin1=10)
        self.preview_text.tag_configure("msg_me",
            foreground="#2d3748", font=("微软雅黑", 9),
            background="#e8f0fe", relief=tk.FLAT,
            lmargin1=30, lmargin2=30, rmargin=30,
            spacing1=3, spacing3=3)
        self.preview_text.tag_configure("msg_other",
            foreground="#2d3748", font=("微软雅黑", 9),
            background="#ffffff", relief=tk.FLAT,
            lmargin1=30, lmargin2=30, rmargin=30,
            spacing1=3, spacing3=3)

        result_card = self._make_card(right_panel)
        result_card.grid(row=1, column=0, sticky="nsew")

        result_header = tk.Frame(result_card, bg=CARD_COLOR)
        result_header.pack(fill=tk.X, padx=14, pady=(10, 0))

        self.result_title = tk.Label(result_header, text="分析结果",
                                     font=("微软雅黑", 12, "bold"), fg=TEXT_PRIMARY, bg=CARD_COLOR)
        self.result_title.pack(side=tk.LEFT)

        self.save_btn = tk.Button(result_header, text="保存为文件", font=("微软雅黑", 9, "bold"),
                                  fg="white", bg=ACCENT, activebackground=ACCENT_HOVER,
                                  activeforeground="white", bd=0, cursor="hand2",
                                  padx=12, pady=3, command=self.save_result, state=tk.DISABLED)
        self.save_btn.pack(side=tk.RIGHT)

        self.result_text = scrolledtext.ScrolledText(result_card, font=("微软雅黑", 10),
                                                     bg=CARD_COLOR, fg=TEXT_PRIMARY,
                                                     bd=0, padx=12, pady=8,
                                                     wrap=tk.WORD, state=tk.DISABLED,
                                                     insertbackground=TEXT_PRIMARY)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 10))

    def _make_tag(self, parent, text, index):
        var = tk.BooleanVar(value=False)
        self.group_vars.append(var)

        tag = tk.Frame(parent, bg=TAG_BG, bd=0, highlightthickness=1,
                       highlightbackground=TAG_BORDER, highlightcolor=TAG_BORDER_SELECTED,
                       cursor="hand2", padx=10, pady=5)
        tag.pack(fill=tk.X, padx=4, pady=2)

        lbl = tk.Label(tag, text=text, font=("微软雅黑", 9),
                       fg=TAG_FG, bg=TAG_BG, cursor="hand2")
        lbl.pack()

        def update_style(*_):
            if var.get():
                tag.config(bg=TAG_BG_SELECTED, highlightbackground=TAG_BORDER_SELECTED)
                lbl.config(fg=TAG_FG_SELECTED, bg=TAG_BG_SELECTED)
            else:
                tag.config(bg=TAG_BG, highlightbackground=TAG_BORDER)
                lbl.config(fg=TAG_FG, bg=TAG_BG)
            self._update_selected_count()

        var.trace_add("write", update_style)

        def toggle(e=None):
            self._on_tag_click(index)

        tag.bind("<Button-1>", toggle)
        lbl.bind("<Button-1>", toggle)

        tag.bind("<Enter>", lambda e: tag.config(bg=TAG_BG_HOVER) if not var.get() else None)
        tag.bind("<Leave>", lambda e: update_style())
        lbl.bind("<Enter>", lambda e: tag.config(bg=TAG_BG_HOVER) if not var.get() else None)
        lbl.bind("<Leave>", lambda e: update_style())

        self.group_tags.append(tag)

    def _on_tag_click(self, index):
        var = self.group_vars[index]
        var.set(not var.get())
        if var.get():
            self._load_single_preview(index)
        else:
            self._remove_single_preview(index)
        self._update_selected_count()

    def _load_single_preview(self, index):
        group = self.groups[index]
        group_name = group.get('displayName', group.get('username', '未知群聊'))
        talker = group.get('username', '')

        selected = self.get_selected_groups()
        group_names = ", ".join([g.get('displayName', g.get('username', '未知')) for g in selected])
        self.preview_title.config(text=f"消息预览")
        self.preview_hint.config(text="加载中...")

        def fetch():
            messages = get_messages(talker, limit=50)

            def update_ui():
                self.preview_text.config(state=tk.NORMAL)

                if self.preview_text.get("1.0", tk.END).strip() in ("", "选择群聊后展示近50条消息"):
                    self.preview_text.delete("1.0", tk.END)

                if messages:
                    self._insert_group_header(group_name)
                    for msg in messages:
                        self._insert_message_bubble(msg)
                    self.preview_text.insert(tk.END, "\n")

                selected = self.get_selected_groups()
                self.preview_hint.config(text=f"共 {len(selected)} 个群聊")
                self.preview_text.config(state=tk.DISABLED)
                self.preview_text.see(tk.END)

            self.root.after(0, update_ui)

        threading.Thread(target=fetch, daemon=True).start()

    def _remove_single_preview(self, index):
        group = self.groups[index]
        group_name = group.get('displayName', group.get('username', '未知群聊'))

        self.preview_text.config(state=tk.NORMAL)
        content = self.preview_text.get("1.0", tk.END)
        lines = content.split('\n')

        new_lines = []
        skip = False
        for line in lines:
            stripped = line.strip()
            if stripped == group_name:
                skip = True
                continue
            if skip and stripped == "":
                skip = False
                continue
            if not skip:
                new_lines.append(line)

        self.preview_text.delete("1.0", tk.END)
        result = '\n'.join(new_lines).strip()
        if not result:
            self.preview_text.insert(tk.END, "选择群聊后展示近50条消息")
            self.preview_hint.config(text="")
        else:
            self.preview_text.insert(tk.END, result + "\n")
            selected = self.get_selected_groups()
            self.preview_hint.config(text=f"共 {len(selected)} 个群聊")

        self.preview_text.config(state=tk.DISABLED)

    def _insert_group_header(self, group_name):
        self.preview_text.insert(tk.END, f"  {group_name}  ", "group_name")
        self.preview_text.insert(tk.END, "\n")

    def _insert_message_bubble(self, msg):
        create_time = msg.get("createTime", 0)
        time_str = datetime.fromtimestamp(create_time).strftime("%H:%M") if create_time else ""
        is_send = msg.get("isSend", 0)
        sender = "我" if is_send else msg.get("senderUsername", "")
        content = msg.get("parsedContent", msg.get("content", ""))
        media_type = msg.get("mediaType", "")

        if media_type == "image":
            content = "[图片]"
        elif media_type == "voice":
            content = "[语音]"
        elif media_type == "video":
            content = "[视频]"
        elif media_type == "emoji":
            content = "[表情]"

        if is_send:
            self.preview_text.insert(tk.END, f"  {time_str} ", "time")
            self.preview_text.insert(tk.END, f"{sender}\n", "sender_me")
            self.preview_text.insert(tk.END, f"    {content}\n", "msg_me")
        else:
            self.preview_text.insert(tk.END, f"  {time_str} ", "time")
            self.preview_text.insert(tk.END, f"{sender}\n", "sender_other")
            self.preview_text.insert(tk.END, f"    {content}\n", "msg_other")

    def _update_selected_count(self):
        count = sum(1 for v in self.group_vars if v.get())
        if count > 0:
            self.selected_count_label.config(text=f"已选 {count} 个")
        else:
            self.selected_count_label.config(text="")

    def load_groups(self):
        self.status_var.set("正在加载群聊...")
        self.root.update()

        self.groups = get_group_sessions()

        for widget in self.tag_inner_frame.winfo_children():
            widget.destroy()
        self.group_vars = []
        self.group_tags = []

        for i, group in enumerate(self.groups):
            display_name = group.get('displayName', group.get('username', '未知群聊'))
            self._make_tag(self.tag_inner_frame, display_name, i)

        self._update_selected_count()
        self.status_var.set(f"已加载 {len(self.groups)} 个群聊")

    def select_all(self):
        for i, var in enumerate(self.group_vars):
            if not var.get():
                var.set(True)
                self._load_single_preview(i)
        self._update_selected_count()

    def deselect_all(self):
        for i, var in enumerate(self.group_vars):
            if var.get():
                var.set(False)
                self._remove_single_preview(i)
        self._update_selected_count()

    def get_selected_groups(self):
        return [self.groups[i] for i, var in enumerate(self.group_vars) if var.get()]

    def _fetch_messages_text(self, groups):
        all_text = ""
        for group in groups:
            group_name = group.get('displayName', group.get('username', '未知群聊'))
            talker = group.get('username', '')
            messages = get_messages(talker, limit=MESSAGES_NUM)
            if messages:
                all_text += format_messages_for_ai(messages, group_name) + "\n\n"
        return all_text

    def _show_result(self, title, result, result_type):
        self.current_result = result
        self.current_result_type = result_type
        self.result_title.config(text=title)
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, result)
        self.result_text.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.NORMAL)
        self.status_var.set("分析完成")

    def _run_in_thread(self, task):
        self.status_var.set("正在分析...")
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, "正在获取聊天记录并分析，请稍候...")
        self.result_text.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        thread = threading.Thread(target=task, daemon=True)
        thread.start()

    def _do_analysis(self, prompt, title, result_type):
        selected = self.get_selected_groups()
        if not selected:
            messagebox.showwarning("提示", "请至少选择一个群聊")
            return

        def task():
            messages_text = self._fetch_messages_text(selected)
            if not messages_text.strip():
                self.root.after(0, lambda: self._show_result("分析结果", "未找到相关聊天记录", ""))
                return
            result = call_ai(prompt, messages_text)
            self.root.after(0, lambda: self._show_result(f"{title} - 分析结果", result, result_type))

        self._run_in_thread(task)

    def do_ask(self):
        selected = self.get_selected_groups()
        if not selected:
            messagebox.showwarning("提示", "请至少选择一个群聊")
            return

        ask_win = tk.Toplevel(self.root)
        ask_win.title("智能问答")
        ask_win.geometry("520x260")
        ask_win.configure(bg=BG_COLOR)
        ask_win.resizable(False, False)
        ask_win.transient(self.root)
        ask_win.grab_set()

        tk.Label(ask_win, text="请输入您的问题", font=("微软雅黑", 12, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_COLOR).pack(padx=20, pady=(16, 8), anchor=tk.W)

        question_entry = scrolledtext.ScrolledText(ask_win, font=("微软雅黑", 10),
                                                   height=4, wrap=tk.WORD, bd=1,
                                                   relief=tk.SOLID)
        question_entry.pack(padx=20, fill=tk.X)
        question_entry.focus_set()

        def submit():
            question = question_entry.get("1.0", tk.END).strip()
            if not question:
                messagebox.showwarning("提示", "请输入问题")
                return
            ask_win.destroy()

            def task():
                messages_text = self._fetch_messages_text(selected)
                if not messages_text.strip():
                    self.root.after(0, lambda: self._show_result("分析结果", "未找到相关聊天记录", ""))
                    return
                prompt = f"{ASK_PROMPT}\n\n问题：{question}\n\n聊天记录："
                result = call_ai(prompt, messages_text)
                self.root.after(0, lambda: self._show_result("智能问答 - 分析结果", result, "智能问答"))

            self._run_in_thread(task)

        btn_frame = tk.Frame(ask_win, bg=BG_COLOR)
        btn_frame.pack(pady=12)
        self._make_action_btn(btn_frame, "提交", BTN_ASK, submit).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="取消", font=("微软雅黑", 10),
                  fg=TEXT_SECONDARY, bg="#e0e0e0", bd=0, cursor="hand2",
                  padx=20, pady=6, command=ask_win.destroy).pack(side=tk.LEFT, padx=6)

    def do_important(self):
        self._do_analysis(IMPORTANT_PROMPT, "重要事项", "重要事项")

    def do_agency(self):
        self._do_analysis(AGENCY_PROMPT, "待办事项", "待办事项")

    def save_result(self):
        if not self.current_result:
            messagebox.showwarning("提示", "没有可保存的结果")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{self.current_result_type}_{timestamp}.txt"

        filepath = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialdir=APP_DIR
        )

        if not filepath:
            return

        selected = self.get_selected_groups()
        group_names = ", ".join([g.get('displayName', g.get('username', '未知')) for g in selected])

        content = (
            f"{self.current_result_type}记录\n"
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"涉及群聊：{group_names}\n"
            f"{'='*50}\n\n"
            f"{self.current_result}"
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        self.status_var.set(f"已保存到 {os.path.basename(filepath)}")
        messagebox.showinfo("保存成功", f"文件已保存到：\n{filepath}")


def main():
    root = tk.Tk()
    app = WeFlowAssistantGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()