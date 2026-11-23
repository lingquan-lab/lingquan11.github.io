---
layout: post
title: "2×2脉动阵列数字IC后端全流程实录"
date: 2026-11-22 20:30:00 +0800
categories: 项目实录
tags: [数字IC, 脉动阵列]
image:
  path: /assets/img/posts/2026-11-22-systolic2x2-asic-backend/cover.webp
  alt: 2×2 脉动阵列的 GDS 版图（截取中部）
---

空闲时间把2×2脉动阵列的数字IC后端完整跑通。https://github.com/lingquan11/systolic2x2-asic-backend  ＜这是我最后一篇发在空间/朋友圈的长文。从这篇起，学习笔记都发在这个博客上。

做完前端的RTL和验证之后，后端用全开源工具链+SKY130工艺库head on：形式等价检查-综合映射到标准单元-静态时序分析-布局布线-生成GDS版图-DRC-LVS-DRC校验-LVS版图和网表校验
可惜的是时序最后差0.25ns没收敛；DFT也没做；DRC/LVS只用了开源工具检查。

然而，这一整套流程能让我完整跑通，靠的完全是开源工具链和开源工艺库。ic设计行业真正的生产环境层层设防的。说到底，这个生态筛选新人的方式不是看学习能力，而是先看门票与title。我进不了那个窄门，知识和经验只在高墙里面循环。

所以接下来收尾cpp矩乘仓库后，主线会转到AI Infra上，先从CUDA算子做起：工具链是开源的，开源生态也很好。成果能公开、能被复现、能交流，反馈也快得多。
