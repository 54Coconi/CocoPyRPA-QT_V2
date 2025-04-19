# CocoPyRPA-QT_V2

> 该仓库是[CocoPyRPA-QT](https://gitee.com/i54Coconi/CocoPyRPA-QT)的全新V2版本代码仓库，由于代码几乎重构所以另存到该仓库下

## 一、程序界面预览

### 1. 主窗口

![主窗口.png](https://s2.loli.net/2025/03/21/nvHlc7Nx1pWLsDg.png)



### 2. 设置界面

![设置界面.png](https://s2.loli.net/2025/03/21/IYDNTuBRKbkv9ns.png)



### 3. 自动执行管理器界面

![自动执行管理器界面.png](https://s2.loli.net/2025/03/21/Sva7hF2YPCT5V8J.png)



### 4. 鼠标录制器标签界面

![鼠标录制器标签界面.png](https://s2.loli.net/2025/03/21/Lo36845wISMdEFf.png)



### 5. 键盘录制器标签界面

![键盘录制器标签界面.png](https://s2.loli.net/2025/03/21/wXrITKdeYjQGa3p.png)



### 6.代码编辑器界面

![代码编辑器界面.png](https://s2.loli.net/2025/03/21/iowBKxVdZ3HyQu6.png)



### 7.功能说明界面

![功能说明界面.png](https://s2.loli.net/2025/03/21/Mq3PF1lRo542gmJ.png)



### 8. 关于界面

![关于界面.png](https://s2.loli.net/2025/03/21/VhcRzN6pUqf5XvM.png)



### 9. 各个主题

![各个主题.png](https://s2.loli.net/2025/03/21/DW4v26AyzLBlYwI.png)



##  二、功能演示

[Bilibili视频](https://www.bilibili.com/video/BV1PrkWYHETX/)



##  三、文件结构

###  1. 源码文件结构

![源码文件结构.png](https://s2.loli.net/2025/03/21/1Nfm9GsHTKb7rvu.png)



### 2. core模块目录结构

![core模块目录结构.png](https://s2.loli.net/2025/03/21/rZ9DhtjQMmRH3AE.png)



### 3. ui模块目录结构

![ui模块目录结构.png](https://s2.loli.net/2025/03/21/LQO9KuFcs8MIpGX.png)



## 四、使用说明

1. 本软件支持前台和后台执行自动化任务：

- 前台执行：手动点击软件工具栏的三种运行模式按钮之一即可

- 后台执行：在”自动执行管理器“界面选择需要自动触发执行的脚本文件（.json文件），然后选择相应的触发器，最后开启自动执行按钮即可

2. 指令运行期间可以通过按下组合键 `Q + Esc` 来中断执行，这对于前台和后台执行均有效



## 五、打包

打包前先安装`Pyinstaller`库，然后 运行项目根目录下的`Pyinstaller.py`文件即可快速打包为exe可执行程序

注意：

- 在打包结束后 **"dist"** 目录下应该只有 **"\_internal"** 目录和 **"run.exe"** 文件，直接运行 "run.exe" 是不能成功执行的，需要将项目里的 **"config"、"models"、"resource"、"ui"** 四个文件夹复制到和 "run.exe" 同级的目录下（软件实际需要的是resource目录下的theme文件夹和ui目录下的static文件夹）；
- 然后在该目录下新建一个空的 "work" 文件夹；
- 最后将 **"mklml.dll"** 文件复制到该目录下，**这一步很重要不然软件无法运行**

完整的打包后文件结构如下图所示：

![打包目录结构.png](https://s2.loli.net/2025/04/18/SVQvJwEU5jrGFml.png)

