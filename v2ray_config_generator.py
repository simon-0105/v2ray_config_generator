# -*- coding: utf-8 -*-
"""
本脚本用于从V2Ray/Xray订阅链接下载服务器列表，并生成适用于V2Ray/Xray客户端的config.json文件。

主要功能：
1. 从指定的URL下载base64编码的订阅内容。
2. 解码订阅内容，提取VMess服务器配置。
3. 基于提取的服务器信息，生成一个完整的V2Ray/Xray配置文件，包括inbounds, outbounds, routing等。
4. 为每个服务器节点创建独立的SOCKS5入站代理，并生成一个inbound-outbound的映射关系文件。
5. 生成两个版本的配置文件：一个只监听本地地址(127.0.0.1)，另一个监听所有网络接口(0.0.0.0)。

使用方法：
- 通过URL下载并生成配置:
  python v2ray_config_generator.py -u "你的订阅链接"
- 从本地文件生成配置:
  python v2ray_config_generator.py -f "./server_list/file_downloaded.txt"
"""

import os
import sys
import argparse
import requests
import base64
import json
import pandas as pd
from urllib.parse import urlparse, unquote

# --- 默认配置常量 ---
DEFAULT_SOCKS_PORT = 50001
DEFAULT_HTTP_PORT = 51001
DEFAULT_OUT_SERVER_INDEX = 29
SERVER_LIST_PATH = "./server_list"
CONFIG_PATH = "./config"
DEFAULT_SUBSCRIBE_FILE = os.path.join(SERVER_LIST_PATH, "downloaded_subscription.txt")
DECODED_URLS_FILE = os.path.join(SERVER_LIST_PATH, "decoded_server_urls.txt")
SERVER_DETAILS_FILE = os.path.join(SERVER_LIST_PATH, "parsed_server_details.txt")
V2RAY_CONFIG_FILE = os.path.join(CONFIG_PATH, "config.json")
INBOUND_OUTBOUND_MAP_FILE = os.path.join(CONFIG_PATH, "inbound_outbound_map.json")
INBOUND_OUTBOUND_MAP_CSV_FILE = os.path.join(CONFIG_PATH, "inbound_outbound_map.csv")


def download_subscription_content(url, output_path):
    """
    从给定的URL下载订阅内容并保存到文件。

    Args:
        url (str): 订阅链接URL。
        output_path (str): 保存下载内容的文件路径。
    """
    try:
        print(f"Downloading subscription content from: {url} ...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 如果请求失败则抛出HTTPError
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download completed.")
    except requests.exceptions.RequestException as e:
        sys.exit(f"Failed to download subscription link: {e}")


def extract_vmess_servers_from_subscription(
    subscription_file_path, decoded_urls_file, server_details_file
):
    """
    从下载的订阅文件中读取内容，解码并提取VMess服务器列表。

    Args:
        subscription_file_path (str): 包含base64编码订阅内容的文件路径。
        decoded_urls_file (str): 保存解码后URL列表的文件路径。
        server_details_file (str): 保存解析后服务器详情列表的文件路径。

    Returns:
        list: 包含VMess服务器配置字典的列表。
    """
    print(f"Reading subscription file from: {subscription_file_path}")
    try:
        with open(subscription_file_path, 'r') as f:
            base64_content = f.read()
        
        decoded_content = base64.b64decode(base64_content).decode('utf-8')
        urls = [unquote(url) for url in decoded_content.splitlines() if url.strip()]

        with open(decoded_urls_file, 'w', encoding="utf-8") as f:
            f.write('\n\n'.join(urls))

        vmess_servers = []
        for url in urls:
            if url.startswith("vmess://"):
                try:
                    vmess_base64_str = url[8:]
                    vmess_json_str = base64.b64decode(vmess_base64_str).decode('utf-8')
                    server_config = json.loads(vmess_json_str)
                    vmess_servers.append(server_config)
                except (json.JSONDecodeError, base64.binascii.Error) as e:
                    print(f"Skipping invalid VMess URL. Error: {e}\nURL: {url}")
                    continue
        
        with open(server_details_file, 'w', encoding="utf-8") as f:
            for server in vmess_servers:
                f.write(json.dumps(server, ensure_ascii=False, indent=2))
                f.write('\n\n')
        
        return vmess_servers
    except FileNotFoundError:
        sys.exit(f"Error: Subscription file not found at {subscription_file_path}")
    except Exception as e:
        sys.exit(f"An error occurred while processing the subscription file: {e}")


def create_tls_settings(server_config):
    """
    根据服务器配置生成TLS设置。
    """
    tls_settings = {
        "serverName": server_config.get("sni", server_config.get("host", "")),
        "allowInsecure": False, # 通常建议设为False更加安全
    }
    if server_config.get("alpn"):
        tls_settings["alpn"] = server_config.get("alpn").split(",")
    return tls_settings


def create_log_config():
    """生成日志配置。"""
    return {"access": "", "error": "", "loglevel": "warning"}


def create_dns_config():
    """生成DNS配置。"""
    return {
        "hosts": {
            "dns.google": "8.8.8.8",
            "proxy.example.com": "127.0.0.1",
        },
        "servers": [
            {
                "address": "1.1.1.1",
                "skipFallback": True,
                "domains": [
                  "domain:googleapis.cn",
                  "domain:gstatic.com"
                ]
            },
            {
                "address": "223.5.5.5",
                "skipFallback": True,
                "domains": [
                    "geosite:cn",
                    "geosite:geolocation-cn"
                ],
                "expectIPs": [
                    "geoip:cn"
                ]
            },
            "1.1.1.1",
            "8.8.8.8",            
            "https://dns.google/dns-query",
            {
                "address": "223.5.5.5",
                "domains": [
                  "tanz-board.01byx31qzn.download"
                ],
                "skipFallback": True
            }
        ],
    }


def create_inbounds_config(vmess_servers, socks_port_start, http_port_start, listen_address):
    """
    为每个服务器节点创建SOCKS5和HTTP入站。

    Args:
        vmess_servers (list): VMess服务器列表。
        socks_port_start (int): SOCKS5入站的起始端口。
        http_port_start (int): HTTP入站的起始端口。
        listen_address (str): 监听地址 ('127.0.0.1' for local, '0.0.0.0' for LAN).

    Returns:
        list: V2Ray入站配置列表。
    """
    inbounds = []
    for i, _ in enumerate(vmess_servers):
        socks_port = socks_port_start + i
        http_port = http_port_start + i
        inbounds += [
            # SOCKS5入站
            {
                "tag": f"socks5-{socks_port}",
                "port": socks_port,
                "listen": listen_address,
                "protocol": "socks",
                "sniffing": {"enabled": True, "destOverride": ["http", "tls"], "routeOnly": False},
                "settings": {"auth": "noauth", "udp": True, "allowTransparent": False}
            },
            # HTTP入站
            {
                "tag": f"http-{http_port}",
                "port": http_port,
                "listen": listen_address,
                "protocol": "http",
                "sniffing": {"enabled": True, "destOverride": ["http", "tls"], "routeOnly": False},
                "settings": {"auth": "noauth", "udp": True, "allowTransparent": False}
            },
        ]
    return inbounds


def create_vnext_server_config(server_config):
    """
    根据单个服务器配置生成vnext对象。
    """
    return {
        "address": server_config["add"],
        "port": int(server_config["port"]),
        "users": [
            {
                "id": server_config["id"],
                "alterId": int(server_config["aid"]),
                "email": "t@t.tt",
                "security": server_config.get("scy", "auto"),
            }
        ]
    }


def create_single_outbound(server_config):
    """
    为单个VMess服务器创建出站配置。

    Args:
        server_config (dict): 单个服务器的配置信息。

    Returns:
        dict: V2Ray出站配置。
    """
    outbound = {
        "tag": server_config["ps"],
        "protocol": "vmess",
        "settings": {
            "vnext": [create_vnext_server_config(server_config)],
        },
        "streamSettings": {
            "network": server_config.get("net", "tcp"),
            "security": server_config.get("tls", "none"),
        },
        "mux": {
            "enabled": server_config.get("mux", {}).get("enabled", False),
            "concurrency": server_config.get("mux", {}).get("concurrency", -1)
        }       
    }

    # 根据网络类型添加特定设置
    network = outbound["streamSettings"]["network"]
    if network == "ws":
        outbound["streamSettings"]["wsSettings"] = {
            "path": server_config.get("path", "/"),
            "headers": {
                "Host": server_config.get("host", server_config["add"])
            }
        }
    
    # 添加TLS设置
    if outbound["streamSettings"]["security"] == "tls":
        outbound["streamSettings"]["tlsSettings"] = create_tls_settings(server_config)

    return outbound


def create_outbounds_config(vmess_servers):
    """
    创建所有出站配置，包括代理、direct和block。

    Args:
        vmess_servers (list): VMess服务器列表。

    Returns:
        list: V2Ray出站配置列表。
    """
    outbounds = [create_single_outbound(server) for server in vmess_servers]
    
    # 添加直连和阻止出站
    outbounds.append({"tag": "direct", "protocol": "freedom", "settings": {}})
    outbounds.append({
        "tag": "block",
        "protocol": "blackhole",
        "settings": {"response": {"type": "http"}}
    })
    
    return outbounds


def create_routing_config(vmess_servers, socks_port_start, http_port_start):
    """
    创建路由规则，并将每个SOCKS入站映射到一个出站。

    Args:
        vmess_servers (list): VMess服务器列表。
        socks_port_start (int): SOCKS5入站的起始端口。
        http_port (int): HTTP入站的端口。

    Returns:
        tuple: 包含路由配置和in-out映射表的元组。
    """
    routing_rules = {
        "domainStrategy": "AsIs",
        "rules": [
            {
                "type": "field",
                "inboundTag": ["api"], 
                "outboundTag": "api"
            },
            {
                "type": "field",
                "outboundTag": vmess_servers[DEFAULT_OUT_SERVER_INDEX].get("ps"),
                "domain": [
                  "domain:googleapis.cn",
                  "domain:gstatic.com"
                ]
            },
            {
                "type": "field", 
                "port": "443", 
                "network": "udp", 
                "outboundTag": "block"
            },            
            {
                "type": "field",
                "outboundTag": "direct",
                "ip": [
                  "geoip:private"
                ]
            },      
            {
                "type": "field", 
                "outboundTag": "direct", 
                "domain": ["geosite:cn", "geosite:geolocation-cn"]
            },
            {
                "type": "field",
                "outboundTag": "direct",
                "domain": [
                  "domain:alidns.com",
                  "domain:doh.pub",
                  "domain:dot.pub",
                  "domain:360.cn",
                  "domain:onedns.net",                  
                ]
            },
            {
                "type": "field",
                "outboundTag": "direct",
                "ip": [
                    "223.5.5.5",
                    "223.6.6.6",
                    "2400:3200::1",
                    "2400:3200:baba::1",
                    "119.29.29.29",
                    "1.12.12.12",
                    "120.53.53.53",
                    "2402:4e00::",
                    "2402:4e00:1::",
                    "180.76.76.76",
                    "2400:da00::6666",
                    "114.114.114.114",
                    "114.114.115.115",
                    "114.114.114.119",
                    "114.114.115.119",
                    "114.114.114.110",
                    "114.114.115.110",
                    "180.184.1.1",
                    "180.184.2.2",
                    "101.226.4.6",
                    "218.30.118.6",
                    "123.125.81.6",
                    "140.207.198.6",
                    "1.2.4.8",
                    "210.2.4.8",
                    "52.80.66.66",
                    "117.50.22.22",
                    "2400:7fc0:849e:200::4",
                    "2404:c2c0:85d8:901::4",
                    "117.50.10.10",
                    "52.80.52.52",
                    "2400:7fc0:849e:200::8",
                    "2404:c2c0:85d8:901::8",
                    "117.50.60.30",
                    "52.80.60.30"
                ]
            },
            {
                "type": "field",
                "outboundTag": "direct",
                "ip": [
                  "geoip:cn"
                ]
      },
        ]
    }
    
    inbound_outbound_map = {}
    
    # HTTP, SOCKS入站与出站一对一映射
    for i, server in enumerate(vmess_servers):
        socks_port = socks_port_start + i
        http_port = http_port_start + i
        socks_inbound_tag = f"socks5-{socks_port}"   
        http_inbound_tag = f"http-{http_port}"             
        outbound_tag = server.get("ps")
        
        routing_rules["rules"].append(
            {
                "type": "field",
                "inboundTag": [socks_inbound_tag, http_inbound_tag],
                "outboundTag": outbound_tag,
            }            
        )
        inbound_outbound_map[f"{socks_inbound_tag} / {http_inbound_tag}"] = outbound_tag
        
    return routing_rules, inbound_outbound_map


def build_v2ray_config(vmess_servers, socks_port, http_port, listen_address):
    """
    根据服务器列表和监听地址生成V2Ray配置字典。

    Args:
        vmess_servers (list): VMess服务器列表。
        socks_port (int): SOCKS5起始端口。
        http_port (int): HTTP起始端口。
        listen_address (str): 监听地址 ('127.0.0.1' 或 '0.0.0.0')。

    Returns:
        tuple: 包含V2Ray配置字典和in-out映射表的元组。
    """
    routing_config, in_out_map = create_routing_config(vmess_servers, socks_port, http_port)

    v2ray_config = {
        "log": create_log_config(),
        "dns": create_dns_config(),
        "inbounds": create_inbounds_config(vmess_servers, socks_port, http_port, listen_address),
        "outbounds": create_outbounds_config(vmess_servers),
        "routing": routing_config,
    }
    return v2ray_config, in_out_map


def main():
    """
    主入口函数，处理命令行参数并启动配置生成流程。
    """
    parser = argparse.ArgumentParser(
        description="Generate V2Ray config from a subscription link.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-u", "--url",
        help="V2Ray subscription link to download from."
    )
    parser.add_argument(
        "-f", "--file",
        default=DEFAULT_SUBSCRIBE_FILE,
        help=f"Local subscription file path.\n(default: {DEFAULT_SUBSCRIBE_FILE})"
    )
    parser.add_argument(
        "-o", "--output",
        default=V2RAY_CONFIG_FILE,
        help=f"Base output V2Ray config file path.\n(default: {V2RAY_CONFIG_FILE})\n"
             "Two files will be generated: [output]_local.json and [output]_lan.json"
    )
    parser.add_argument(
        "-m", "--map",
        default=INBOUND_OUTBOUND_MAP_FILE,
        help=f"Output In-Out map file path.\n(default: {INBOUND_OUTBOUND_MAP_FILE})"
    )
    parser.add_argument(
        "--socks_port",
        type=int,
        default=DEFAULT_SOCKS_PORT,
        help=f"Starting SOCKS inbound port.\n(default: {DEFAULT_SOCKS_PORT})"
    )
    parser.add_argument(
        "--http_port",
        type=int,
        default=DEFAULT_HTTP_PORT,
        help=f"Starting HTTP inbound port.\n(default: {DEFAULT_HTTP_PORT})"
    )

    args = parser.parse_args()

    # 确保输出目录存在
    os.makedirs(SERVER_LIST_PATH, exist_ok=True)
    os.makedirs(CONFIG_PATH, exist_ok=True)

    subscription_file = args.file
    # 如果提供了URL，则下载订阅内容
    if args.url:
        download_subscription_content(args.url, subscription_file)
    
    if not os.path.exists(subscription_file):
        sys.exit(f"Subscription file not found at '{subscription_file}'. Please provide a file using -f or a URL using -u.")

    vmess_servers = extract_vmess_servers_from_subscription(
        subscription_file, DECODED_URLS_FILE, SERVER_DETAILS_FILE
    )
    
    if not vmess_servers:
        sys.exit("No valid VMess servers found in the subscription.")

    # 生成本地监听配置 (127.0.0.1)
    v2ray_config_local, in_out_map = build_v2ray_config(
        vmess_servers, args.socks_port, args.http_port, "127.0.0.1"
    )

    # 生成局域网监听配置 (0.0.0.0)
    v2ray_config_lan, _ = build_v2ray_config(
        vmess_servers, args.socks_port, args.http_port, "0.0.0.0"
    )

    # 确定输出文件名
    output_base = args.output
    base_name, ext = os.path.splitext(output_base)
    if not ext:
        ext = ".json"
        base_name = output_base
    
    local_config_file = f"{base_name}_local{ext}"
    lan_config_file = f"{base_name}_lan{ext}"

    # 写入本地监听的V2Ray配置文件
    with open(local_config_file, "w", encoding="utf-8") as f:
        json.dump(v2ray_config_local, f, ensure_ascii=False, indent=2)
    print(f"V2Ray config file (local) generated at: {local_config_file}")

    # 写入局域网监听的V2Ray配置文件
    with open(lan_config_file, "w", encoding="utf-8") as f:
        json.dump(v2ray_config_lan, f, ensure_ascii=False, indent=2)
    print(f"V2Ray config file (LAN) generated at: {lan_config_file}")

    # 写入In-Out映射文件 (JSON)
    with open(args.map, "w", encoding="utf-8") as f:
        json.dump(in_out_map, f, ensure_ascii=False, indent=2)
    print(f"In-Out map JSON file generated at: {args.map}")

    # 写入In-Out映射文件 (CSV)
    df = pd.DataFrame(list(in_out_map.items()), columns=['Inbound (Tag/Port)', 'Outbound (Tag)'])
    df.to_csv(INBOUND_OUTBOUND_MAP_CSV_FILE, encoding="utf-8_sig", index=False)
    print(f"In-Out map CSV file generated at: {INBOUND_OUTBOUND_MAP_CSV_FILE}")


if __name__ == "__main__":
    main()
