# PikPak WebDAV 视频播放器

## 简介
这是一个基于Flask的WebDAV视频播放器，专为PikPak网盘设计，可适用于任何支持WebDAV协议的网盘。它解决了中文路径和特殊字符编码问题，使视频播放更加流畅可靠。

## 主要功能
- 基于ID的文件导航系统，完全避免路径编码问题
- 支持视频文件播放和媒体信息读取
- 自动生成播放列表
- 持久化存储映射关系，重启后依然可用
- 支持搜索功能
- 支持列表/网格视图切换
- 黑暗模式支持

## 系统要求
- Python 3.6+
- Flask
- Flask-CORS
- Requests
- lxml

## 安装
```bash
git clone https://github.com/your-username/V0-PikPak-WebDAV.git
cd V0-PikPak-WebDAV
pip install -r requirements.txt
```

## 使用方法
1. 运行Flask应用
```bash
python app.py
```

2. 在浏览器中访问 `http://localhost:5000`
3. 输入你的WebDAV服务地址、用户名和密码进行连接
4. 浏览并播放视频文件

## 项目结构
- app.py: 后端Flask应用
- static/: 前端静态资源
  - js/: JavaScript文件
  - css/: CSS样式表
  - index.html: 主页面

## 版本
当前版本: 0.10.0 - 查看[更新日志](CHANGELOG.md)了解详情
