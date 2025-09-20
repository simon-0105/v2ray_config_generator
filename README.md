# V2Ray Config Generator

[English](#en) | [中文](#zh)

<div id="zh"></div>

## V2Ray 订阅链接转换与配置生成器

这是一个 Python 脚本，用于从 V2Ray/Xray 订阅链接中提取服务器节点信息，并生成一个功能完整的 `config.json` 客户端配置文件。

脚本的核心功能是将订阅链接中的每一个服务器节点映射为一个本地的 SOCKS5 和 HTTP 入站代理。这样，你就可以通过连接不同的本地端口来快速切换使用不同的服务器节点，而无需频繁修改配置文件。

### ✨ 主要功能

-   **自动下载和解码**：从指定的 URL 下载订阅内容，并自动完成 Base64 解码。
-   **多节点配置**：为订阅链接中的每一个 VMess 服务器节点生成独立的出站（outbound）配置。
-   **端口映射**：为每个服务器节点创建独立的 SOCKS5 和 HTTP 入站（inbound）代理，端口号自动递增。
-   **双版本配置**：
    -   `config_local.json`：只监听本地回环地址 (`127.0.0.1`)，仅供本机使用。
    -   `config_lan.json`：监听所有网络接口 (`0.0.0.0`)，可供局域网内的其他设备使用。
-   **生成映射表**：生成一个 `inbound_outbound_map.csv` 和 `.json` 文件，清晰地展示了本地端口与服务器节点的对应关系。
-   **内置路由规则**：包含一套常用的路由规则，可实现国内外流量自动分流（例如，中国大陆网站直连）。

### 📦 安装依赖

在运行脚本之前，请确保你已经安装了 Python，然后通过 pip 安装所需的库：

```bash
pip install -r requirements.txt
```

### 🚀 使用方法

你可以通过命令行参数来运行此脚本。

1.  **从 URL 下载并生成配置** (推荐):

    将 `"你的订阅链接"` 替换为你的真实 V2Ray/Xray 订阅链接。

    ```bash
    python v2ray_config_generator.py -u "你的订阅链接"
    ```

2.  **从本地文件生成配置**:

    如果你已经手动下载了订阅文件（通常是一个 base64 编码的文本文件），可以使用 `-f` 参数。

    ```bash
    python v2ray_config_generator.py -f "/path/to/your/subscription.txt"
    ```

#### 命令行参数详解

-   `-u`, `--url`: V2Ray/Xray 订阅链接。如果提供此参数，脚本会先下载订阅内容。
-   `-f`, `--file`: 本地订阅文件的路径。默认为 `./server_list/downloaded_subscription.txt`。
-   `-o`, `--output`: 生成的 V2Ray 配置文件基础路径。默认为 `./config/config.json`。脚本会在此基础上生成 `_local.json` 和 `_lan.json` 两个文件。
-   `-m`, `--map`: 生成的入站-出站映射文件的路径。默认为 `./config/inbound_outbound_map.json`。
-   `--socks_port`: SOCKS5 入站的起始端口号。默认为 `50001`。
-   `--http_port`: HTTP 入站的起始端口号。默认为 `51001`。

### 📁 生成的文件结构

运行脚本后，会在当前目录下生成以下文件和文件夹：

```
.
├── config/
│   ├── config_local.json             # V2Ray 配置文件 (监听 127.0.0.1)
│   ├── config_lan.json               # V2Ray 配置文件 (监听 0.0.0.0)
│   ├── inbound_outbound_map.json     # 端口与服务器节点的映射关系 (JSON 格式)
│   └── inbound_outbound_map.csv      # 端口与服务器节点的映射关系 (CSV 格式)
│
├── server_list/
│   ├── downloaded_subscription.txt   # 从 URL 下载的原始订阅内容
│   ├── decoded_server_urls.txt       # 解码后的服务器链接 (vmess://...)
│   └── parsed_server_details.txt     # 解析后的服务器配置详情
│
└── v2ray_config_generator.py         # 脚本本身
```

### 💡 如何使用生成的配置

1.  从 `config` 文件夹中选择一个配置文件 (`config_local.json` 或 `config_lan.json`)。
2.  将其重命名为 `config.json` 并放入你的 V2Ray/Xray 客户端的目录中。
3.  启动 V2Ray/Xray。
4.  查阅 `inbound_outbound_map.csv` 文件，找到你想要使用的服务器节点及其对应的本地 SOCKS5/HTTP 端口。
5.  将你的浏览器或系统代理设置为该本地端口（例如 `socks5://127.0.0.1:50001`），即可通过对应的服务器节点上网。

### 📄 许可证

该项目采用 [MIT License](LICENSE) 授权。

---

<div id="en"></div>

## V2Ray Config Generator

This Python script extracts server node information from a V2Ray/Xray subscription link and generates a feature-rich `config.json` for client use.

The core functionality of this script is to map each server node from the subscription link to a local SOCKS5 and HTTP inbound proxy. This allows you to quickly switch between different server nodes by connecting to different local ports, without needing to frequently modify the configuration file.

### ✨ Features

-   **Auto-Download & Decode**: Downloads subscription content from a given URL and automatically handles Base64 decoding.
-   **Multi-Node Configuration**: Generates individual outbound configurations for each VMess server node in the subscription.
-   **Port Mapping**: Creates separate SOCKS5 and HTTP inbound proxies for each server node with auto-incrementing port numbers.
-   **Dual-Version Configs**:
    -   `config_local.json`: Listens only on the local loopback address (`127.0.0.1`) for local use.
    -   `config_lan.json`: Listens on all network interfaces (`0.0.0.0`), allowing other devices on the LAN to connect.
-   **Mapping Table Generation**: Creates `inbound_outbound_map.csv` and `.json` files, clearly showing the correspondence between local ports and server nodes.
-   **Built-in Routing Rules**: Includes a common set of routing rules to automatically bypass traffic for specific regions (e.g., direct connection for mainland China websites).

### 📦 Installation

Before running the script, ensure you have Python installed. Then, install the required libraries using pip:

```bash
pip install -r requirements.txt
```

### 🚀 Usage

Run the script via the command line.

1.  **Generate Config from URL** (Recommended):

    Replace `"your_subscription_link"` with your actual V2Ray/Xray subscription link.

    ```bash
    python v2ray_config_generator.py -u "your_subscription_link"
    ```

2.  **Generate Config from a Local File**:

    If you have already downloaded the subscription file (usually a base64 encoded text file), use the `-f` flag.

    ```bash
    python v2ray_config_generator.py -f "/path/to/your/subscription.txt"
    ```

#### Command-Line Arguments

-   `-u`, `--url`: The V2Ray/Xray subscription link. If provided, the script will download the content first.
-   `-f`, `--file`: Path to a local subscription file. Defaults to `./server_list/downloaded_subscription.txt`.
-   `-o`, `--output`: Base path for the generated V2Ray config file. Defaults to `./config/config.json`. The script will generate `_local.json` and `_lan.json` variants.
-   `-m`, `--map`: Path for the generated inbound-outbound map file. Defaults to `./config/inbound_outbound_map.json`.
-   `--socks_port`: The starting port number for SOCKS5 inbounds. Defaults to `50001`.
-   `--http_port`: The starting port number for HTTP inbounds. Defaults to `51001`.

### 📁 Generated File Structure

After running the script, the following files and directories will be created:

```
.
├── config/
│   ├── config_local.json             # V2Ray config (listens on 127.0.0.1)
│   ├── config_lan.json               # V2Ray config (listens on 0.0.0.0)
│   ├── inbound_outbound_map.json     # Port-to-server mapping (JSON format)
│   └── inbound_outbound_map.csv      # Port-to-server mapping (CSV format)
│
├── server_list/
│   ├── downloaded_subscription.txt   # Raw subscription content from URL
│   ├── decoded_server_urls.txt       # Decoded server links (vmess://...)
│   └── parsed_server_details.txt     # Parsed server configuration details
│
└── v2ray_config_generator.py         # The script itself
```

### 💡 How to Use the Generated Config

1.  Choose a configuration file from the `config` directory (`config_local.json` or `config_lan.json`).
2.  Rename it to `config.json` and place it in your V2Ray/Xray client's directory.
3.  Start V2Ray/Xray.
4.  Consult the `inbound_outbound_map.csv` file to find the server node you want to use and its corresponding local SOCKS5/HTTP port.
5.  Set your browser or system proxy to that local port (e.g., `socks5://127.0.0.1:50001`) to start using the internet through the corresponding server node.

### 📄 License

This project is licensed under the [MIT License](LICENSE).
