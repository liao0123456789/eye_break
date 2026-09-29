# eye_break

> 看 20 分钟屏幕，就看 20 秒 6 米外的东西。

一个轻量的 Windows 桌面护眼提醒工具。基于 PyQt6，支持间隔提醒、定点闹钟、自定义音乐、贴边隐藏、系统托盘。双击直接运行，无需安装

---

## 为什么做这个

天天对着电脑，眼睛扛不住。看到网上说有个 **20/20/20 法则**：看 20 分钟屏幕，就看 20 秒 20 英尺（约 6 米）外的东西，能缓解眼疲劳。

道理都懂，但一专注、一上头就忘了。想定个每 20 分钟的闹钟，结果发现：

- 手机闹钟要一个一个设，几十个太麻烦
- 电脑上没有特别合适的软件
- 有些软件只能设固定时间，不能循环间隔

---

## 功能

- ⏱ **间隔提醒**：每 N 分钟提醒一次休息，间隔可自定义
- 🔔 **定点闹钟**：支持设置多个固定时间点（如 09:00、15:00），和间隔提醒互不冲突
- 🪟 **悬浮小窗**：靠近屏幕边缘自动缩进去，鼠标移过去又弹出来，不遮挡视线
- 🎵 **自定义提示音**：可以用系统默认提示音，也可以选自己本地的音乐文件
- 📌 **系统托盘**：点 `－` 最小化到托盘，不占任务栏
- 💾 **设置记忆**：位置、间隔、音乐、闹钟都会保存，下次打开还在

---

## 截图

### 悬浮窗 

<img width="496" height="383" alt="597be4cb40911c55e13f7e4d832f103c" src="https://github.com/user-attachments/assets/065495a9-fa02-419c-8509-9d9ba02f77d9" />


### 到点提示卡片

<img width="381" height="298" alt="18008149a4249c14f1407ac26d26132b" src="https://github.com/user-attachments/assets/dd6841e4-10db-4c03-abe3-4048d3612fe4" />


### 定点闹钟设置
<img width="271" height="269" alt="0af3c4d6e5abdab5a6a2e92c1fe61375" src="https://github.com/user-attachments/assets/91d5de49-66a7-4441-8890-c44ab9ddcd17" />



---

## 使用

### 方式一：直接下载 exe

到 [Releases](../../releases) 页面下载最新的 `eye_break.zip`，解压后，双击运行exe即可。

> ⚠️ exe 是 PyInstaller 打包的，**没有代码签名**。Windows Defender 或部分杀毒软件可能会提示"未知发布者"甚至误报，点"仍要运行"即可。
>
> 介意安全性的，可以看源码自己打包（见下文）。

### 方式二：从源码运行

最好Python 3.10+。

```bash
git clone https://github.com/你的用户名/eye_break.git
cd eye_break
pip install -r requirements.txt
python main.py





有新功能要求可在issue里提或者加qq群反馈：1125370541
