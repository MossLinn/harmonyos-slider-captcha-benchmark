# 滑块验证码定位与拖动 Benchmark（完整包 v2）

该包用于自有 HarmonyOS 模拟器测试应用中的 GUI Agent/CV 定位评测，不用于绕过第三方线上验证服务。

## 目录

- `src/cv_locator/`：方形滑块、不规则拼图检测，鲁棒性评测，拖动动作生成与模拟器端到端测试。
- `datasets/slider_puzzle_realistic_v2/`：4 组照片场景拼图数据、标注、mask、检测可视化及 manifest。
- `app/captcha_login_benchmark/`：HarmonyOS 验证码测试应用完整可构建源码。
- `app/headless_ime/`：用于模拟器自动化的无软键盘 HarmonyOS 输入法源码与 HDC 控制脚本。
- `prebuilt/captcha-login-benchmark-unsigned.hap`：已构建测试应用。
- `evidence/captcha_login_benchmark/`：截图、Layout、标注图、鲁棒性结果和拖动流水线报告。
- `ground_truth/captcha_login_benchmark.json`：测试应用功能层级 Ground Truth。

## Python 环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r src/cv_locator/requirements.txt
```

## 离线检测

带 HarmonyOS Layout 的方形滑块：

```bash
python src/cv_locator/detect_puzzle.py \
  --image evidence/captcha_login_benchmark/puzzle_street.png \
  --layout evidence/captcha_login_benchmark/puzzle_street.json \
  --annotated /tmp/puzzle-annotated.png
```

照片场景中的不规则拼图：

```bash
python src/cv_locator/detect_jigsaw.py \
  --image datasets/slider_puzzle_realistic_v2/bridge/panel.png \
  --annotated /tmp/jigsaw-annotated.png
```

把目标比例拼接成拖动动作：

```bash
python src/cv_locator/build_drag_action.py \
  --image evidence/captcha_login_benchmark/drag_pipeline/street_before.png \
  --layout evidence/captcha_login_benchmark/drag_pipeline/street_before.json \
  --target-percent 72 --duration-ms 500
```

## 测试应用安装

```bash
HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
$HDC -t 127.0.0.1:5555 install -r prebuilt/captcha-login-benchmark-unsigned.hap
```

Bundle 名：`com.hmtest.captchalogin`。

应用源码不含依赖、Hvigor 缓存和中间编译文件；在新设备用 DevEco Studio Sync 后可重新构建。预构建 HAP 已单独保留。

## 无软键盘输入法

`app/headless_ime` 是用于 HarmonyOS 模拟器 UI 遍历的无界面输入法。编辑框获得焦点时，它保存当前 `InputClient` 并立即调用 `KeyboardController.hide()`，不创建软键盘面板。主机侧通过 HDC 的 `uitest uiInput` 向已聚焦编辑框注入文本。

```bash
cd app/headless_ime
python3 scripts/headless_ime.py install \
  entry/build/default/outputs/default/entry-default-unsigned.hap
python3 scripts/headless_ime.py choose
python3 scripts/headless_ime.py insert '中文输入测试'
```

Bundle 名：`com.hmtest.headlessime`。完整构建、启用和输入命令见 `app/headless_ime/README.md`。

## 已有结果

普通横向滑块的三个模拟器端到端场景均验证通过：street 72%、lake 45%、cafe 63%。详细坐标、检测结果和验证后的 UI 状态见 `evidence/captcha_login_benchmark/drag_pipeline/`。

`direct_drag_pipeline/` 是自由拖动拼图的扩展实验；主横向滑块流水线仍采用源块与目标处于同一水平行的约束。
