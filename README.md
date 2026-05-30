# BiliWatchlater Agent (V0.1)

一个基于Python的B站稍后再看列表动态同步工具，旨在为后续AI智能体推荐提供持久化数据基础

## 功能特点

- 自动获取B站稍后再看列表
- 采用Diff算法动态增删改本地CSV数据，保留本地自定义扩展列

## 快速开始

1. 安装依赖：`pip install -r requirements.txt`
2. 配置配置：复制`env.example`为`.env`并填写你的B站Cookie
3. 运行：`python get_line.py`