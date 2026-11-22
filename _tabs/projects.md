---
title: 项目
icon: fas fa-flask
order: 0
---

做过和在做的项目，数字均取自仓库记录与[关于]({{ '/about/' | relative_url }})页，测法和环境见各仓库。

## C++矩阵乘法性能分析与优化

**进行中** · 2026年10月起 · 计划12月10日前收尾

- 只换循环顺序：128阶快 **8.45倍**，256阶快 **9.38倍**，各尺寸跑5次、全部通过
- 分块实验75条全过；分块64在分块组最快，但128和256阶仍慢于ikj，负结果照实记
- 已完成 Day 1–8：正确性验证、计时口径、循环顺序、分块、编译选项对照；下一步 SIMD

[GitHub：cpp-matmul-performance](https://github.com/lingquan11/cpp-matmul-performance) · [项目起点]({{ '/2026/10/22/cpp-matmul-start/' | relative_url }})

## 1×4脉动阵列乘加单元

**已完成** · 独立完成 · Verilog / Python / Yosys

- 规格：权重固定、无符号8位输入、24位累加、部分和双级寄存器对齐
- Python 金标准模型独立对拍，自检 testbench，4个定向用例（含满量程）功能仿真全过
- Yosys 综合 **1859个单元、227个触发器**，无锁存器、无组合环、无警告
- 未做：工艺库映射、时序分析、布局布线（通用综合）

[GitHub：systolic-mac-1x4](https://github.com/lingquan11/systolic-mac-1x4) · [开学两个月小记录]({{ '/2026/11/08/systolic-mac-1x4/' | relative_url }})

## FPGA上板验证

**已完成** · 2026年11月14日 · 正点原子达芬奇Pro（XC7A100T）

- Vivado 综合实现通过，时序收敛：**Setup WNS +0.049ns**，违例终点0
- 比特流烧录成功，板上4个内置用例实测 **4/4 通过**
- 定位并解决 Digilent Adept 运行库与 Win11 不兼容导致的下载器故障

## ai-chip-explorer：科研方向探索 Skill

**第一版已开源** · 持续完善中

- 了解各方向在研究和工作中做什么，通过对话和轻量小项目找到感兴趣的方向
- 从零寻找科研 idea 或打磨已有想法；默认聚焦 AI 芯片

[GitHub：ai-chip-explorer](https://github.com/lingquan11/ai-chip-explorer) · [开源说明]({{ '/2026/10/29/ai-chip-explorer/' | relative_url }})

## RoboMaster 3SE战队电控组

**机械爪分组**

- GM6020 独立驱动；DM4310 接入战队工程当天跑通 CAN 收发、使能和反馈解析
- 电机内置串级PI上单变量整定，定案 KP 94、KI 2、速度上限 4rad/s
