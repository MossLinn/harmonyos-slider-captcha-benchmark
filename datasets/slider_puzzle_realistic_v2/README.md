# Realistic jigsaw slider samples v2

四个受控离线样本，采用现实场景照片和带凹凸卡口的拼图轮廓。每个样本目录包含：

- `background.png`：无验证元素的底图；
- `challenge.png`：移动块和暗化缺口；
- `panel.png`：带滑轨的完整测试画面；
- `mask.png`：像素级拼图形状掩码。

`manifest.json` 记录块体框、缺口框、目标百分比、拖动距离、滑轨和目标触控坐标。
底图由内置 imagegen 生成；拼图块和缺口由确定性生成器创建，因此块体内容与目标区域严格匹配。

重新生成：

```bash
python benchmark/tools/cv_locator/generate_jigsaw_dataset.py
```

仅用于自有 GUI Agent 与 UI 自动化 Benchmark，不用于绕过第三方验证码服务。
