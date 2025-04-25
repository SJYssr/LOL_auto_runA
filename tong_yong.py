# _*_coding : UTF_8 _*_
# author : SJYssr
# Date : 2025/3/7 下午3:21
# ClassName : tong_yong.py
# Github : https://github.com/SJYssr
import json
import threading
import time
from ctypes import POINTER, c_ulong, Structure, c_ushort, c_short, c_long, byref, windll, pointer, sizeof, Union
import pyWinhook
import pythoncom
import requests
import wx
import wx.adv
import urllib3

urllib3.disable_warnings()
zhilianUrl = "https://127.0.0.1:2999/liveclientdata/activeplayer"

def getAttackSpeed():
    try:
        r = requests.get(zhilianUrl, verify=False)
        if r.ok:
            lolJson = r.text
            data = json.loads(lolJson)
            res = float(data["championStats"]["attackSpeed"])
            r.close()
            return res
        else:
            return None
    except:
        return None

PUL = POINTER(c_ulong)

class KeyBdInput(Structure):
    # 定义一个名为KeyBdInput的结构体类，继承自Structure
    _fields_ = [("wVk", c_ushort),
                # 定义结构体的字段wVk，类型为c_ushort（无符号短整型），通常用于表示虚拟键码
                ("wScan", c_ushort),
                # 定义结构体的字段wScan，类型为c_ushort（无符号短整型），通常用于表示硬件扫描码
                ("dwFlags", c_ulong),
                # 定义结构体的字段dwFlags，类型为c_ulong（无符号长整型），用于表示附加标志（如按键状态）
                ("time", c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(Structure):
    _fields_ = [("uMsg", c_ulong),
                ("wParamL", c_short),
                ("wParamH", c_ushort)]

class MouseInput(Structure):
    _fields_ = [("dx", c_long),
                ("dy", c_long),
                ("mouseData", c_ulong),
                ("dwFlags", c_ulong),
                ("time", c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(Structure):
    _fields_ = [("type", c_ulong),
                ("ii", Input_I)]

class POINT(Structure):
    _fields_ = [("x", c_ulong),
                ("y", c_ulong)]

def get_mpos():
    orig = POINT()
    windll.user32.GetCursorPos(byref(orig))
    return int(orig.x), int(orig.y)

def set_mpos(pos):
    x, y = pos
    windll.user32.SetCursorPos(x, y)

def move_click(pos, move_back=False):
    origx, origy = get_mpos()
    set_mpos(pos)
    FInputs = Input * 2
    extra = c_ulong(0)
    ii_ = Input_I()
    ii_.mi = MouseInput(0, 0, 0, 2, 0, pointer(extra))
    ii2_ = Input_I()
    ii2_.mi = MouseInput(0, 0, 0, 4, 0, pointer(extra))
    x = FInputs((0, ii_), (0, ii2_))
    windll.user32.SendInput(2, pointer(x), sizeof(x[0]))
    if move_back:
        set_mpos((origx, origy))
        return origx, origy

def sendkey(scancode, pressed):
    FInputs = Input * 1
    extra = c_ulong(0)
    ii_ = Input_I()
    flag = 0x8
    ii_.ki = KeyBdInput(0, 0, flag, 0, pointer(extra))
    InputBox = FInputs((1, ii_))
    if scancode is None:
        return
    InputBox[0].ii.ki.wScan = scancode
    InputBox[0].ii.ki.dwFlags = 0x8

    if not (pressed):
        InputBox[0].ii.ki.dwFlags |= 0x2

    windll.user32.SendInput(1, pointer(InputBox), sizeof(InputBox[0]))

class TaskBarIcon(wx.adv.TaskBarIcon):
    ID_About = wx.NewIdRef()
    ID_Close = wx.NewIdRef()

    def __init__(self, frame):
        wx.adv.TaskBarIcon.__init__(self)
        self.frame = frame
        self.SetIcon(wx.Icon(name='icon.ico'), '摇头怪上线！')
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.OnTaskBarLeftDClick)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=self.ID_About)
        self.Bind(wx.EVT_MENU, self.OnClose, id=self.ID_Close)

    def OnTaskBarLeftDClick(self, event):
        if self.frame.IsIconized():
            self.frame.Iconize(False)
        if not self.frame.IsShown():
            self.frame.Show(True)
        self.frame.Raise()

    def OnAbout(self, event):
        wx.MessageBox("本程序前提是基于LOL改键,不用担心封号\n"
                      "请进游戏到设置修改:\n"
                      "快捷攻击型移动，选择设置成 Z \n"
                      "玩家移动点击，选择设置成 X \n"
                      "仅针对目标英雄设置为 C \n"
                      "最好把窗口设置为无边框模式或者窗口模式\n"
                      "最好再设置下优先攻击鼠标最近的单位，这样就可以鼠标指哪打那\n"
                      "按键说明：\n"
                      "长按CapsLock - 触发走A\n"
                      "Esc - 最小化到托盘区\n"
                      "pgup -调出窗口并开启\n"
                      "pgdown - 调出窗口并关闭\n"
                      "ins - 设置触发按键\n"
                      "鼠标中间滚轮按下 - 设置攻速识别位置\n"
                      "作者：https://github.com/SJYssr\n", '使用帮助')

    def OnClose(self, event):
        self.Destroy()
        self.frame.Destroy()

    def CreatePopupMenu(self):
        menu = wx.Menu()
        menu.Append(self.ID_About, '使用帮助')
        menu.Append(self.ID_Close, '退出')
        return menu

class MainWindow(wx.Frame):
    minTime = 0.1
    onlyLoL = True
    currentKey = "Capital"
    GongSu = 0.7
    QianYao = 0.35  # 固定前摇比例
    YDBC = 0.0     # 固定移动补偿
    dc = 1.0 / GongSu
    qy = dc * QianYao
    hy = dc - qy + YDBC

    press_the_trigger_button = False

    def onKeyDown(self, event):
        if event.Key == self.currentKey:
            self.press_the_trigger_button = True
            if self.onlyLoL and not self.isPause:
                sendkey(0x2e, 1)
            return self.isPause
        elif event.Key == "Prior":
            self.isPause = False
            self.SetTransparent(255)
            self.message_text.Label = "已启动,按住[" + self.currentKey + "]走A"
            self.Iconize(False)
            return False
        elif event.Key == "Next":
            self.isPause = True
            self.SetTransparent(90)
            self.message_text.Label = "已关闭"
            self.Iconize(False)
            return False
        elif event.Key == "Insert":
            self.start_setting = True
            self.currentKey = ""
            self.message_text.Label = "按任意键完成绑定"
            self.Iconize(False)
            return False
        elif not self.IsIconized() and event.Key == "Escape":
            self.Iconize(True)
            return False
        elif self.start_setting:
            self.currentKey = event.Key
            self.start_setting = False
            self.message_text.Label = "已经绑定到：" + self.currentKey
            self.Iconize(False)
            return False
        return True

    def onKeyUp(self, event):
        if event.Key == self.currentKey:
            self.press_the_trigger_button = False
            if self.onlyLoL:
                sendkey(0x2e, 0)
            return self.isPause
        return True

    def action(self):
        while True:
            if self.press_the_trigger_button and not self.isPause:
                self.click(0x2c, self.qy)
                self.click(0x2d, self.hy)
            else:
                time.sleep(0.01)

    def click(self, key, click_time):
        while click_time > self.minTime and self.press_the_trigger_button:
            process_time = time.time()
            sendkey(key, 1)
            sendkey(key, 0)
            time.sleep(self.minTime)
            click_time = click_time - (time.time() - process_time)
        if self.press_the_trigger_button and click_time >= 0:
            sendkey(key, 1)
            sendkey(key, 0)
            time.sleep(click_time)

    def key_listener(self):
        hm = pyWinhook.HookManager()
        hm.KeyDown = self.onKeyDown
        hm.KeyUp = self.onKeyUp
        hm.HookKeyboard()
        hm.HookMouse()
        pythoncom.PumpMessages()

    def listenerAttackSpeed(self):
        while True:
            time.sleep(0.2)
            speed = getAttackSpeed()
            if speed is None:
                continue
            if speed <= 0:
                continue
            if self.GongSu == speed:
                continue
            self.GongSu = speed
            self.dc = 1.0 / self.GongSu
            self.qy = self.dc * self.QianYao
            self.hy = self.dc - self.qy + self.YDBC

    def OnClose(self, event):
        self.Iconize(True)

    def __init__(self, parent, title):
        # 初始化wx.Frame，设置窗口标题、位置、样式和大小
        wx.Frame.__init__(self, parent, title=title, pos=wx.DefaultPosition, style=wx.DEFAULT_FRAME_STYLE ^ (
                wx.MAXIMIZE_BOX | wx.SYSTEM_MENU) | wx.STAY_ON_TOP,
                          size=(176, 130))

        # 设置窗口背景颜色为白色
        self.SetBackgroundColour("#ffffff")
        # 设置窗口图标
        self.SetIcon(wx.Icon('icon.ico'))
        # 创建任务栏图标对象
        self.taskBarIcon = TaskBarIcon(self)
        # 绑定窗口关闭事件
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        # 初始化暂停状态和设置状态为False
        self.isPause = False
        self.start_setting = False

        # 创建垂直布局管理器
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        # 创建水平布局管理器
        self.sizer4 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer5 = wx.BoxSizer(wx.HORIZONTAL)

        # 创建开始按钮
        self.button_start = wx.Button(self, name="start", label="开", size=(40, 30))
        # 创建停止按钮
        self.button_stop = wx.Button(self, name="stop", label="关", size=(40, 30))
        # 创建设置触发键按钮
        self.button_setting = wx.Button(self, name="setting", label="设触发键", size=(80, 30))
        # 绑定按钮点击事件
        self.Bind(wx.EVT_BUTTON, self.onClick, self.button_start)
        self.Bind(wx.EVT_BUTTON, self.onClick, self.button_stop)
        self.Bind(wx.EVT_BUTTON, self.onClick, self.button_setting)
        # 将按钮添加到水平布局管理器
        self.sizer4.Add(self.button_start, flag=wx.ALIGN_CENTER)
        self.sizer4.Add(self.button_stop, flag=wx.ALIGN_CENTER)
        self.sizer4.Add(self.button_setting, flag=wx.ALIGN_CENTER)

        # 创建静态文本，显示当前状态和提示信息
        self.message_text = wx.StaticText(self, name="aa", label="已启动,按住[" + self.currentKey + "]走A\n进入游戏后自动获取攻速")
        # 设置文本颜色为黑色
        self.message_text.SetForegroundColour('#000000')
        # 将静态文本添加到水平布局管理器
        self.sizer5.Add(self.message_text)

        # 将水平布局管理器添加到垂直布局管理器
        self.sizer.Add(self.sizer4)
        self.sizer.Add(self.sizer5)

        # 设置窗口的布局管理器
        self.SetSizer(self.sizer)
        # 显示窗口
        self.Show(True)

        # 创建线程，分别用于执行动作、监听按键和监听攻速
        self.thread_key = threading.Thread(target=self.action)
        self.thread_action = threading.Thread(target=self.key_listener)
        self.thread_listenerAttackSpeed = threading.Thread(target=self.listenerAttackSpeed)
        # 设置线程为守护线程
        self.thread_listenerAttackSpeed.daemon = True
        self.thread_key.daemon = True
        self.thread_action.daemon = True
        # 启动线程
        self.thread_listenerAttackSpeed.start()
        self.thread_key.start()
        self.thread_action.start()

    def onClick(self, event):
        name = event.GetEventObject().GetName()
        if name == "start":
            self.isPause = False
            self.SetTransparent(255)
            self.message_text.Label = "已启动,按住[" + self.currentKey + "]走A"
        elif name == "stop":
            self.isPause = True
            self.SetTransparent(90)
            self.message_text.Label = "已关闭"
        elif name == "setting":
            self.start_setting = True
            self.currentKey = ""
            self.message_text.Label = "按任意键完成绑定"

app = wx.App(False)
ui = MainWindow(None, "摇头怪已上线!")
ui.Centre()
app.MainLoop()