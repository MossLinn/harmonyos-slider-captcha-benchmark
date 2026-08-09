# HmTest Headless IME

用于鸿蒙模拟器 UI 遍历的无界面输入法。编辑框获得焦点时，输入法保存当前
`InputClient` 并立即调用 `KeyboardController.hide()`，不会创建软键盘面板。

主机脚本通过 HDC 的 `uitest uiInput` 注入文本和按键，支持中文文本、退格和
Enter。输入法扩展运行在系统隔离沙箱中，因此这里不额外开启网络端口。

## 构建与安装

```bash
export JAVA_HOME=/Applications/DevEco-Studio.app/Contents/jbr/Contents/Home
export DEVECO_SDK_HOME=/Applications/DevEco-Studio.app/Contents/sdk
export OHOS_SDK_HOME=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony
/Applications/DevEco-Studio.app/Contents/tools/ohpm/bin/ohpm install
/Applications/DevEco-Studio.app/Contents/tools/hvigor/bin/hvigorw assembleHap --mode module \
  -p module=entry@default -p product=default -p buildMode=debug --no-daemon

python3 scripts/headless_ime.py install entry/build/default/outputs/default/entry-default-unsigned.hap
python3 scripts/headless_ime.py choose
```

`choose` 使用模拟器自带的 `ime -e/-s` 命令启用并切换输入法。聚焦目标编辑框后：

```bash
python3 scripts/headless_ime.py insert '中文与 emoji ✅'
python3 scripts/headless_ime.py delete 2
python3 scripts/headless_ime.py clear
python3 scripts/headless_ime.py enter
```

该项目只用于本机模拟器/测试设备。注入前必须先点击目标编辑框，使其获得焦点。

## 截图保护

本项目不绕过其他应用的防截屏保护。对自有应用，应在 debug 构建中关闭隐私窗口
配置；无法修改源码的应用使用 UI Tree/无障碍节点作为遍历证据。以下命令会同时
保存截图和 UI Tree，即使截图受保护，遍历器仍可使用结构化节点：

```bash
python3 scripts/capture_evidence.py ./evidence --bundle com.example.app
```
