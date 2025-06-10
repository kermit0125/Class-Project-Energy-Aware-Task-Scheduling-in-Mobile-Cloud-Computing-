# ⚙️ Energy-Aware Task Scheduling in Mobile Cloud Computing  
# ⚙️ 移动云计算环境下的能耗感知任务调度算法课程作业

This repository contains the coursework implementation of the **energy- and performance-aware task scheduling algorithm** from:  
Lin, X., Wang, Y., Xie, Q., & Pedram, M. (2014, June).  
*Energy and Performance-Aware Task Scheduling in a Mobile Cloud Computing Environment*.  
In 2014 IEEE 7th Int’l Conference on Cloud Computing (pp. 192–199). IEEE.

本项目为东北大学 EECE 7205《嵌入式系统设计》课程作业，基于上述论文实现了移动设备与云端协同的任务调度算法，旨在演示如何在执行时间与能耗之间进行权衡。

---

## 🧩 Background | 项目背景

Task scheduling in mobile cloud computing must balance **execution time** and **energy consumption**.  
本项目模拟多核设备与云端节点协同下的调度场景，使用有向任务图和执行时间表来演示算法流程。

---

## 🚀 Features | 功能简介

- 初始调度：根据任务依赖和多核/云端执行时间进行分配  
- 优化调度：在初始结果上应用迁移策略，进一步降低总能耗  
- 能耗计算：统计各核心与无线通信的能量消耗  
- 可视化：生成 Gantt-style 调度图和调度表

---

## 🛠 Technologies Used | 技术栈

- Python 3  
- NetworkX – 任务图建模  
- Matplotlib – 调度可视化  
- NumPy – 数值计算  
- heapq – 优先级队列管理

---

## 📂 Project Structure | 文件结构

```bash
.
├── example1.py              # 示例1：初始调度脚本
├── example1_result.py       # 示例1：调度结果展示
├── Example1_Final.py        # 示例1：优化调度 + 能耗计算
├── example2.py              # 示例2：初始调度
├── Example2_Final.py        # 示例2：优化调度
├── example3.py              # 示例3：初始调度
├── Example3_Final.py        # 示例3：优化调度
├── example4.py              # 示例4：初始调度
├── Example4_Final.py        # 示例4：优化调度
├── example5.py              # 示例5：初始调度
├── Example5_Final.py        # 示例5：优化调度
├── EECE7205_Project2.pptx   # 课程项目演示幻灯片
├── Project2.docx            # 项目报告文档
└── README.md                # 本说明文件
