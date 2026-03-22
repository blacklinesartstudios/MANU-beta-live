"""
💙 Manubeta Trading Assistant — Windows Desktop App
Taskbar tray icon + floating widget
Reads screen, gives trading signals
"""
import tkinter as tk
import threading, time, base64, json, sys, requests
from io import BytesIO

try:
    from PIL import Image, ImageDraw, ImageGrab, ImageTk
    PIL_OK = True
except: PIL_OK = False
try:
    import mss, mss.tools
    MSS_OK = True
except: MSS_OK = False
try:
    import pystray
    from pystray import MenuItem as item
    TRAY_OK = True
except: TRAY_OK = False

# ════════════════════════════
GROQ_KEY      = "YOUR_GROQ_KEY_HERE"
SCAN_INTERVAL = 15
# ════════════════════════════

GROQ_API     = "https://api.groq.com/openai/v1/chat/completions"
VISION_MODEL = "llama-3.2-90b-vision-preview"
TEXT_MODEL   = "llama-3.3-70b-versatile"

SYSTEM = """You are Manubeta — expert Indian stock market AI from Hyderabad.
Analyze trading chart screenshots. Return ONLY valid JSON, nothing else:
{"direction":"LONG or SHORT or WAIT","instrument":"name","entry":number,"sl":number,"t1":number,"t2":number,"t3":number,"confidence":75,"pattern":"pattern name","analysis":"2 sentences Tenglish","warning":"risk warning or empty string"}"""

def make_icon():
    img = Image.new('RGBA', (64,64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.ellipse([2,2,62,62], fill=(13,13,20,255))
    d.ellipse([4,4,60,60], outline=(37,99,235,180), width=3)
    d.ellipse([14,18,34,38], fill=(236,72,153,255))
    d.ellipse([30,18,50,38], fill=(236,72,153,255))
    d.polygon([(14,28),(50,28),(32,52)], fill=(236,72,153,255))
    return img

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.visible   = False
        self.analyzing = False
        self.auto_on   = False

        self.win = tk.Toplevel(self.root)
        self.win.title("Manubeta")
        self.win.attributes('-topmost', True)
        self.win.attributes('-alpha', 0.97)
        self.win.resizable(False, False)
        self.win.overrideredirect(True)
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f"300x490+{sw-316}+{sh-530}")
        self.win.withdraw()
        self._dx = self._dy = 0

        self._ui()
        if TRAY_OK: self._tray()
        else: self.show()
        self.root.mainloop()

    def _ui(self):
        W = self.win
        W.configure(bg='#0d0d0d')

        # Title bar
        tb = tk.Frame(W, bg='#111', height=38, cursor='fleur')
        tb.pack(fill='x')
        tb.pack_propagate(False)
        tb.bind('<Button-1>',  lambda e: setattr(self,'_dx',e.x) or setattr(self,'_dy',e.y))
        tb.bind('<B1-Motion>', lambda e: W.geometry(f'+{W.winfo_x()+e.x-self._dx}+{W.winfo_y()+e.y-self._dy}'))
        tk.Label(tb, text='💙 Manubeta', bg='#111', fg='#60a5fa',
                 font=('Segoe UI',11,'bold')).place(x=10,y=9)
        self.dot = tk.Label(tb, text='●', bg='#111', fg='#00c853', font=('Segoe UI',10))
        self.dot.place(x=258, y=9)
        tk.Label(tb, text='✕', bg='#111', fg='#444', font=('Segoe UI',12),
                 cursor='hand2').place(x=278,y=7) ; tb.winfo_children()[-1].bind('<Button-1>',lambda e:self.hide())

        # Badge
        self.badge = tk.Label(W, text='⏳  WAITING FOR SIGNAL', bg='#141428',
                               fg='#60a5fa', font=('Segoe UI',11,'bold'), pady=10)
        self.badge.pack(fill='x', padx=10, pady=(8,2))
        self.conf = tk.Label(W, text='Scan your chart to begin', bg='#0d0d0d',
                              fg='#333', font=('Segoe UI',8))
        self.conf.pack()

        # Levels
        lf = tk.Frame(W, bg='#0d0d0d'); lf.pack(fill='x', padx=10, pady=3)
        def row(p,lbl,clr):
            f=tk.Frame(p,bg='#141414',pady=5,padx=10); f.pack(fill='x',pady=1)
            tk.Label(f,text=lbl,bg='#141414',fg='#444',font=('Segoe UI',9),width=9,anchor='w').pack(side='left')
            v=tk.Label(f,text='--',bg='#141414',fg=clr,font=('Segoe UI',13,'bold'),anchor='e'); v.pack(side='right')
            return v
        self.e=row(lf,'Entry',   '#60a5fa')
        self.s=row(lf,'SL 🛑',   '#ff5252')
        self.t1=row(lf,'Target 1','#69f0ae')
        self.t2=row(lf,'Target 2','#00e676')
        self.t3=row(lf,'Target 3','#1de9b6')

        # Analysis text
        self.txt = tk.Text(W, height=3, bg='#141414', fg='#999',
                            font=('Segoe UI',8), wrap='word', relief='flat',
                            padx=8, pady=5, state='disabled', border=0)
        self.txt.pack(fill='x', padx=10, pady=3)

        self.warn_lbl = tk.Label(W, text='', bg='#200a0a', fg='#ff8a80',
                                  font=('Segoe UI',8), wraplength=260,
                                  justify='left', padx=8, pady=3)

        # Buttons
        bf = tk.Frame(W, bg='#0d0d0d'); bf.pack(fill='x', padx=10, pady=3)
        self.abtn = tk.Button(bf, text='🔍  Analyze Screen Now',
            bg='#2563eb', fg='white', font=('Segoe UI',10,'bold'),
            relief='flat', pady=8, cursor='hand2',
            activebackground='#1d4ed8', activeforeground='white',
            command=self.analyze)
        self.abtn.pack(fill='x', pady=2)
        self.aubtn = tk.Button(bf, text='▶  Auto Scan Every 15s',
            bg='#141414', fg='#555', font=('Segoe UI',9),
            relief='flat', pady=5, cursor='hand2',
            activebackground='#1a1a1a', activeforeground='#aaa',
            command=self.toggle_auto)
        self.aubtn.pack(fill='x', pady=1)
        self.tlbl = tk.Label(W, text='', bg='#0d0d0d', fg='#2a2a2a', font=('Segoe UI',8))
        self.tlbl.pack()
        tk.Label(W, text='💙 Manaswi కోసం. ఎప్పటికీ.', bg='#0d0d0d',
                 fg='#1a1a1a', font=('Segoe UI',7,'italic')).pack(side='bottom', pady=5)

    def _tray(self):
        ico = make_icon()
        menu = pystray.Menu(
            item('💙 Show / Hide',      lambda: self.win.after(0, self.toggle),  default=True),
            item('🔍 Analyze Now',      lambda: self.win.after(0, self.analyze)),
            pystray.Menu.SEPARATOR,
            item('▶ Start Auto Scan',  lambda: self.win.after(0, self._auto_on)),
            item('⏹ Stop Auto Scan',   lambda: self.win.after(0, self._auto_off)),
            pystray.Menu.SEPARATOR,
            item('❌ Exit Manubeta',    self._exit),
        )
        self.tray = pystray.Icon('Manubeta', ico, '💙 Manubeta Trading', menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def toggle(self):
        if self.visible: self.hide()
        else: self.show()

    def show(self):
        self.win.deiconify(); self.win.lift(); self.visible=True

    def hide(self):
        self.win.withdraw(); self.visible=False

    def _exit(self):
        self.auto_on=False
        if TRAY_OK: self.tray.stop()
        self.root.quit(); sys.exit(0)

    def analyze(self):
        if self.analyzing: return
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self.analyzing = True
        self.win.after(0, lambda: [
            self.badge.config(text='🔍  READING YOUR SCREEN...', bg='#0d1433', fg='#60a5fa'),
            self.abtn.config(text='⏳  Analyzing...', state='disabled', bg='#1a1a2e'),
            self.dot.config(fg='#ffd600')
        ])
        b64 = self._cap()
        try:
            if b64:
                msgs=[{"role":"user","content":[
                    {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64}"}},
                    {"type":"text","text":"Analyze this trading chart. Entry, SL, 3 Targets. JSON only."}]}]
                mdl = VISION_MODEL
            else:
                msgs=[{"role":"user","content":"Sample NIFTY intraday signal. JSON only."}]
                mdl = TEXT_MODEL

            r = requests.post(GROQ_API,
                headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                json={"model":mdl,
                      "messages":[{"role":"system","content":SYSTEM}]+msgs,
                      "max_tokens":400,"temperature":0.2}, timeout=30)
            d = r.json()
            if 'error' in d: raise Exception(d['error']['message'])
            raw = d['choices'][0]['message']['content'].strip().replace('```json','').replace('```','').strip()
            sig = json.loads(raw)
            self.win.after(0, lambda: self._show(sig))
        except Exception as ex:
            self.win.after(0, lambda: self._err(str(ex)))
        self.analyzing=False

    def _cap(self):
        try:
            if MSS_OK:
                with mss.mss() as s:
                    shot=s.grab(s.monitors[0])
                    return base64.b64encode(mss.tools.to_png(shot.rgb,shot.size)).decode()
        except: pass
        try:
            if PIL_OK:
                buf=BytesIO(); ImageGrab.grab().save(buf,'PNG')
                return base64.b64encode(buf.getvalue()).decode()
        except: pass
        return None

    def _show(self, sig):
        d = sig.get('direction','WAIT')
        if   d=='LONG':  self.badge.config(text='📈  LONG — BUY NOW',   bg='#002010', fg='#00e676')
        elif d=='SHORT': self.badge.config(text='📉  SHORT — SELL NOW', bg='#200000', fg='#ff5252')
        else:            self.badge.config(text='⏳  WAIT — No Signal', bg='#1a1500', fg='#ffd600')

        self.conf.config(text=f"Confidence: {sig.get('confidence',0)}%  |  {sig.get('instrument','')}", fg='#555')
        def f(v):
            if v is None: return '--'
            try: return f'{float(v):,.0f}'
            except: return str(v)
        self.e .config(text=f(sig.get('entry')))
        self.s .config(text=f(sig.get('sl')))
        self.t1.config(text=f(sig.get('t1')))
        self.t2.config(text=f(sig.get('t2')))
        self.t3.config(text=f(sig.get('t3')))

        self.txt.config(state='normal'); self.txt.delete(1.0,'end')
        self.txt.insert('end', f"{sig.get('pattern','')}\n{sig.get('analysis','')}")
        self.txt.config(state='disabled')

        w=sig.get('warning','')
        if w: self.warn_lbl.config(text=f'⚠️ {w}'); self.warn_lbl.pack(fill='x',padx=10,pady=2)
        else: self.warn_lbl.pack_forget()

        self.abtn.config(text='🔍  Analyze Screen Now', state='normal', bg='#2563eb')
        self.dot.config(fg='#00c853')
        if not self.visible: self.show()

    def _err(self, msg):
        self.badge.config(text='❌  Error — Check Groq Key', bg='#1a0000', fg='#ff5252')
        self.txt.config(state='normal'); self.txt.delete(1.0,'end')
        self.txt.insert('end', f'Error: {msg}\n\nOpen manubeta_app.py → set GROQ_KEY')
        self.txt.config(state='disabled')
        self.abtn.config(text='🔍  Analyze Screen Now', state='normal', bg='#2563eb')
        self.dot.config(fg='#ff5252'); self.analyzing=False

    def _auto_on(self):
        if not self.auto_on: self.toggle_auto()
    def _auto_off(self):
        if self.auto_on: self.toggle_auto()

    def toggle_auto(self):
        self.auto_on = not self.auto_on
        if self.auto_on:
            self.aubtn.config(text='⏹  Stop Auto Scan', bg='#3d0010', fg='#ff8a80')
            threading.Thread(target=self._loop, daemon=True).start()
        else:
            self.aubtn.config(text='▶  Auto Scan Every 15s', bg='#141414', fg='#555')
            self.tlbl.config(text='')

    def _loop(self):
        while self.auto_on:
            for i in range(SCAN_INTERVAL,0,-1):
                if not self.auto_on: break
                self.win.after(0, lambda t=i: self.tlbl.config(text=f'Next scan in {t}s...'))
                time.sleep(1)
            if self.auto_on:
                self.win.after(0, self.analyze); time.sleep(3)
        self.win.after(0, lambda: self.tlbl.config(text=''))

if __name__=='__main__':
    print("💙 Manubeta Starting...")
    if GROQ_KEY=="YOUR_GROQ_KEY_HERE":
        print("⚠️  Set your GROQ_KEY inside manubeta_app.py first!")
    App()
