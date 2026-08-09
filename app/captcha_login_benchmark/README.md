# Captcha Login Benchmark

用于评估 HarmonyOS UI 遍历器和 GUI Agent 的受控登录样本，包含图形验证码与滑块拼图。
验证码字符和拼图画面均使用 `Canvas` 绘制，UI Layout 只暴露组件类型与通用语义，
不会直接暴露验证码答案或拼图目标位置。

## 固定测试数据

- Bundle：`com.hmtest.captchalogin`
- Ability：`EntryAbility`
- 账号：`testuser`
- 密码：`pass1234`
- 初始图形验证码：`7K3M`
- 拼图背景：街景、山湖、咖啡桌面三种现实场景照片
- 拼图目标：依次为 Slider 值 `72 ± 4`、`45 ± 4`、`63 ± 4`

点击“换一张”后验证码按 `7K3M → A9P4 → Q2F8` 循环。这种固定序列只用于保证
Benchmark 可复现；算法评测时不应从源码或 Ground Truth 向 Agent 泄露答案。
滑块页的“换一张拼图”按街景、山湖、咖啡桌面循环，并清空当前滑块状态。

## 状态流程

```text
账号密码与图形验证码
  ├─ 凭据错误 → 账号或密码错误
  ├─ 验证码错误 → 错误提示并自动换图
  └─ 正确 → 滑块拼图
               ├─ 换一张拼图 → 切换照片和缺口位置
               ├─ 未对齐 → 拼图位置不正确
               └─ 对齐 → 登录按钮启用 → 登录成功 → 重新测试
```

## 构建

```bash
export JAVA_HOME=/Applications/DevEco-Studio.app/Contents/jbr/Contents/Home
export DEVECO_SDK_HOME=/Applications/DevEco-Studio.app/Contents/sdk
export OHOS_SDK_HOME=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony
/Applications/DevEco-Studio.app/Contents/tools/hvigor/bin/hvigorw assembleHap \
  --mode module -p product=default -p module=entry@default -p buildMode=debug --no-daemon
```

HAP 输出：`entry/build/default/outputs/default/entry-default-unsigned.hap`。

## 推荐评测

分别运行三种观察配置并比较任务成功率、动作数和模型调用数：

1. Layout-only：预期能填写表单，但无法可靠读取 Canvas 内容。
2. Screenshot-only：可做视觉任务，但表单定位和状态判定可能不稳定。
3. Screenshot + Layout：视觉识别验证码/缺口，Layout 定位输入框、Slider 和按钮。

Ground Truth 位于 `benchmark/ground_truth/hierarchy/captcha_login_benchmark.json`，动态证据
位于 `benchmark/ground_truth/evidence/captcha_login_benchmark/`。
