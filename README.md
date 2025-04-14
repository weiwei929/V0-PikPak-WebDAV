# PikPak WebDAV

一个允许通过WebDAV协议访问PikPak云存储的代理服务器。

## 功能
- WebDAV连接验证
- 文件浏览
- 文件流媒体播放
- 视频元数据获取
- 播放列表生成

## 安装

### 使用pip安装
```bash
pip install -r requirements.txt
```

### 使用Anaconda安装
```bash
# 创建新环境（如果需要）
conda create -n pikpak-webdav python=3.9
# 激活环境
conda activate pikpak-webdav
# 安装依赖
pip install -r requirements.txt
```

## 运行

### 普通方式启动
```bash
python app.py
```

### Anaconda环境启动
```bash
# 确保已激活环境
conda activate pikpak-webdav
# 启动应用
python app.py
```

### Docker方式启动
```bash
docker-compose up
```

## 使用方法
访问 http://localhost:5000 使用Web界面，或将WebDAV服务器地址设置为 http://localhost:5000
