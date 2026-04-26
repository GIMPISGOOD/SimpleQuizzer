import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import sys
import requests

# ==================== 路径处理（支持 PyInstaller 打包） ====================
def get_base_dir():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return base_dir

def get_file_path(filename):
    return os.path.join(get_base_dir(), filename)

# ==================== 用户管理 ====================
u_f = get_file_path("users.json")
d_k = "你的DeepSeek API密钥"
d_u = "https://api.deepseek.com/v1/chat/completions"

def l_u():
    if os.path.exists(u_f):
        try:
            with open(u_f, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"student1": "123456", "teacher1": "654321"}
    return {"student1": "123456", "teacher1": "654321"}

u_c = l_u()

def s_u():
    try:
        with open(u_f, "w", encoding="utf-8") as f:
            json.dump(u_c, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("保存用户失败:", e)

# ==================== 多题库自动加载 ====================
def load_all_questions(base_dir):
    """自动加载 base_dir 下所有 .json 文件（排除 users.json）中的题目，合并为一个题库"""
    all_questions = []
    loaded_files = 0
    last_data = None
    for file in os.listdir(base_dir):
        if not file.endswith(".json") or file == "users.json":
            continue
        file_path = os.path.join(base_dir, file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                last_data = data
                if isinstance(data, dict) and "questions" in data:
                    qlist = data["questions"]
                    if isinstance(qlist, list):
                        all_questions.extend(qlist)
                        loaded_files += 1
                elif isinstance(data, list):
                    all_questions.extend(data)
                    loaded_files += 1
        except Exception as e:
            print(f"加载文件 {file} 失败: {e}")

    if loaded_files == 0:
        # 尝试加载默认的 题库.json（兼容旧版）
        default_path = get_file_path("题库.json")
        if os.path.exists(default_path):
            try:
                with open(default_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    last_data = data
                    if isinstance(data, dict) and "questions" in data:
                        all_questions = data["questions"]
                    elif isinstance(data, list):
                        all_questions = data
                    loaded_files = 1
            except Exception as e:
                print(f"加载默认题库失败: {e}")

    # 构造返回的题库字典
    if loaded_files == 0:
        return {"subject": "无题目", "grade": "无题目", "questions": []}
    elif loaded_files == 1 and isinstance(last_data, dict):
        subject = last_data.get("subject", "未指定")
        grade = last_data.get("grade", "未指定")
    else:
        subject = "综合题库"
        grade = "多年级混合"
    return {
        "subject": subject,
        "grade": grade,
        "questions": all_questions
    }

# ==================== 登录窗口 ====================
class LW:
    def __init__(self, r):
        self.r = r
        self.r.title("答题器 - 登录")
        self.r.geometry("400x350")
        self.r.resizable(False, False)

        self.f = ttk.Frame(self.r, padding="30")
        self.f.pack(expand=True, fill=tk.BOTH)

        ttk.Label(self.f, text="答题器登录", font=("Arial", 16, "bold")).pack(pady=20)

        ttk.Label(self.f, text="用户名：").pack(anchor=tk.W, pady=5)
        self.u_v = tk.StringVar()
        self.u_e = ttk.Entry(self.f, textvariable=self.u_v, font=("Arial", 12))
        self.u_e.pack(fill=tk.X, pady=5)

        ttk.Label(self.f, text="密码：").pack(anchor=tk.W, pady=5)
        self.p_v = tk.StringVar()
        self.p_e = ttk.Entry(self.f, textvariable=self.p_v, show="*", font=("Arial", 12))
        self.p_e.pack(fill=tk.X, pady=5)

        b_f = ttk.Frame(self.f)
        b_f.pack(fill=tk.X, pady=20)

        ttk.Button(b_f, text="登录", command=self.l).pack(side=tk.LEFT, padx=5)
        ttk.Button(b_f, text="添加账号", command=self.a_u).pack(side=tk.LEFT, padx=5)

    def l(self):
        u = self.u_v.get().strip()
        p = self.p_v.get().strip()

        if not u or not p:
            messagebox.showwarning("警告", "用户名和密码不能为空！")
            return

        if u_c.get(u) == p:
            messagebox.showinfo("成功", "登录成功！")
            self.r.withdraw()
            m_w = tk.Toplevel()
            m_w.protocol("WM_DELETE_WINDOW", self.r.quit)
            AW(m_w)
        else:
            messagebox.showerror("错误", "用户名或密码错误！")

    def a_u(self):
        n_u = simpledialog.askstring("添加账号", "请输入新用户名：")
        if not n_u:
            return
        if n_u in u_c:
            messagebox.showwarning("警告", "用户名已存在！")
            return

        n_p = simpledialog.askstring("添加账号", "请输入新密码：", show="*")
        if not n_p:
            return

        u_c[n_u] = n_p
        s_u()
        messagebox.showinfo("成功", "账号添加并保存成功！")

# ==================== 主窗口（答题器） ====================
class AW:
    def __init__(self, r):
        self.r = r
        self.r.title("答题器 - 主界面")
        self.r.geometry("850x650")
        self.r.minsize(850, 650)

        self.q_b = self.l_q_b()
        self.c_q_i = 0
        self.u_a = {}
        self.s_o = tk.StringVar(value="")
        self.c_w()
        self.l_q()

    def l_q_b(self):
        base_dir = get_base_dir()
        qb = load_all_questions(base_dir)
        if not qb["questions"]:
            messagebox.showerror("错误", f"未找到任何题目文件，请在 {base_dir} 下放置至少一个包含题目的 .json 文件")
        return qb

    def c_w(self):
        t = f"{self.q_b.get('subject', '未知科目')} - {self.q_b.get('grade', '未知年级')} 答题器"
        ttk.Label(self.r, text=t, font=("Arial", 14, "bold")).pack(pady=10)

        self.p_l = ttk.Label(self.r, text="", font=("Arial", 10))
        self.p_l.pack()

        self.q_f = ttk.Frame(self.r, padding="20")
        self.q_f.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)

        self.q_l = ttk.Label(
            self.q_f, text="", font=("Arial", 12), wraplength=780, justify=tk.LEFT
        )
        self.q_l.pack(anchor=tk.W, pady=10)

        self.a_a = ttk.Frame(self.q_f)
        self.a_a.pack(fill=tk.BOTH, expand=True, pady=10)

        self.b_f = ttk.Frame(self.r)
        self.b_f.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(self.b_f, text="上一题", command=self.p_q).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.b_f, text="下一题", command=self.n_q).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.b_f, text="提交全部答案", command=self.s_a).pack(side=tk.RIGHT, padx=5)

    def u_p(self):
        t = len(self.q_b.get("questions", []))
        if t == 0:
            self.p_l.config(text="无题目")
            return
        self.p_l.config(text=f"第 {self.c_q_i + 1}/{t} 题")

    def l_q(self):
        for w in self.a_a.winfo_children():
            w.destroy()

        qs = self.q_b.get("questions", [])
        t = len(qs)
        self.c_q_i = max(0, min(self.c_q_i, t - 1))
        self.u_p()

        if t == 0:
            self.q_l.config(text="暂无题目！")
            return

        q = qs[self.c_q_i]
        q_t = q.get("type", "未知")
        q_x = q.get("question", "")
        self.q_l.config(text=f"【{q_t}】{q_x}")

        if q_t == "选择题":
            self.c_c_b(q.get("options", []))
        elif q_t == "填空题":
            self.c_i("fill")
        elif q_t == "简答题":
            self.c_i("short")

    def c_c_b(self, o):
        self.s_o.set("")
        if self.c_q_i in self.u_a:
            self.s_o.set(self.u_a[self.c_q_i])

        for opt in o:
            if not opt:
                continue
            b = tk.Button(
                self.a_a,
                text=str(opt),
                font=("Arial", 12),
                relief="raised", bd=2,
                bg="#f0f0f0"
            )
            b.config(command=lambda o=opt, b=b: self.s_o_f(o, b))
            b.pack(fill="x", pady=3, padx=10)

            if self.s_o.get() == str(opt):
                b.config(bg="#d0e8ff")

    def s_o_f(self, o, s_b):
        self.s_o.set(o)
        for w in self.a_a.winfo_children():
            if isinstance(w, tk.Button):
                if w == s_b:
                    w.configure(bg="#d0e8ff")
                else:
                    w.configure(bg="#f0f0f0")

    def c_i(self, k):
        if k == "fill":
            self.i_v = tk.StringVar()
            e = ttk.Entry(self.a_a, textvariable=self.i_v, font=("Arial", 12), width=60)
            e.pack(pady=8)
            if self.c_q_i in self.u_a:
                self.i_v.set(self.u_a[self.c_q_i])
        else:
            self.i_t = tk.Text(self.a_a, font=("Arial", 12), height=9, width=90)
            self.i_t.pack(pady=8)
            if self.c_q_i in self.u_a:
                self.i_t.delete(1.0, tk.END)
                self.i_t.insert(1.0, self.u_a[self.c_q_i])

    def s_c(self):
        qs = self.q_b.get("questions", [])
        if self.c_q_i >= len(qs):
            return
        q = qs[self.c_q_i]
        t = q["type"]
        a = ""

        if t == "选择题":
            a = self.s_o.get().strip()
        elif t == "填空题":
            a = self.i_v.get().strip()
        elif t == "简答题":
            if hasattr(self, 'i_t'):
                a = self.i_t.get(1.0, tk.END).strip()

        self.u_a[self.c_q_i] = a

    def p_q(self):
        if self.c_q_i <= 0:
            messagebox.showinfo("提示", "已经是第一题")
            return
        self.s_c()
        self.c_q_i -= 1
        self.l_q()

    def n_q(self):
        t = len(self.q_b.get("questions", []))
        if self.c_q_i >= t - 1:
            messagebox.showinfo("提示", "已经是最后一题")
            return
        self.s_c()
        self.c_q_i += 1
        self.l_q()

    def s_a(self):
        self.s_c()
        qs = self.q_b.get("questions", [])
        if not qs:
            messagebox.showwarning("警告", "暂无题目可提交")
            return

        r = []
        c = 0
        t = len(qs)

        for i, q in enumerate(qs):
            t_q = q["type"]
            q_x = q["question"]
            s = str(q.get("answer", "")).strip()
            u = str(self.u_a.get(i, "")).strip()

            if t_q in ["选择题", "填空题"]:
                o = (u == s)
                if o:
                    c += 1
                m = "✅ 正确" if o else "❌ 错误"
                r.append(f"题目{i+1}：{q_x}\n你的答案：{u}\n标准答案：{s}\n{m}\n")
            else:
                if not u:
                    ai = "未作答"
                else:
                    ai = self.d_g(q_x, u, s)
                r.append(f"【简答题{i+1}】{q_x}\n你的答案：{u}\nAI批改：{ai}\n")

        w = tk.Toplevel(self.r)
        w.title("批改结果")
        w.geometry("750x550")
        t_x = tk.Text(w, font=("Arial", 11))
        s = ttk.Scrollbar(w, command=t_x.yview)
        s.pack(side=tk.RIGHT, fill=tk.Y)
        t_x.config(yscrollcommand=s.set)
        t_x.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        sm = f"\n==== 客观题得分：{c}/{t} ====\n（简答题由AI评语评分）"
        t_x.insert(tk.END, "\n".join(r) + sm)
        t_x.config(state=tk.DISABLED)
        ttk.Button(w, text="关闭", command=w.destroy).pack(pady=5)

    def d_g(self, q, u_a, a):
        if not d_k or d_k == "你的DeepSeek API密钥":
            return "未配置API密钥，无法AI批改"
        try:
            h = {
                "Authorization": f"Bearer {d_k}",
                "Content-Type": "application/json"
            }
            dt = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是批改老师，只简短判断是否正确，20字内"},
                    {"role": "user", "content": f"题目：{q}\n学生答案：{u_a}\n参考答案：{a}"}
                ],
                "temperature": 0.1
            }
            res = requests.post(d_u, headers=h, json=dt, timeout=10)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"AI服务异常：{str(e)}"

# ==================== 程序入口 ====================
if __name__ == "__main__":
    # 检查是否存在任何题目文件，如果没有则生成默认题库
    base = get_base_dir()
    has_any = False
    for f in os.listdir(base):
        if f.endswith(".json") and f != "users.json":
            has_any = True
            break
    if not has_any:
        default_q_path = get_file_path("题库.json")
        sm = {
            "subject": "数学",
            "grade": "一年级",
            "questions": [
                {"type": "选择题", "question": "995后面一个数是？", "answer": "996", "options": ["994", "995", "996"]},
                {"type": "填空题", "question": "7 + 8 = ___", "answer": "15"},
                {"type": "简答题", "question": "什么是加法？", "answer": "把两个数合并成一个数的运算"}
            ]
        }
        try:
            with open(default_q_path, "w", encoding="utf-8") as f:
                json.dump(sm, f, ensure_ascii=False, indent=4)
            print(f"已创建默认题库：{default_q_path}")
        except Exception as e:
            print(f"创建默认题库失败：{e}")

    r = tk.Tk()
    LW(r)
    r.mainloop()
