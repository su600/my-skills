---
name: pi-web-upgrade
description: 升级 pi（@earendil-works/pi-coding-agent）和 pi-web（@agegr/pi-web），然后运行 pi-web-set-logo.py 换 logo，最后重启 pi-web.service。用户说"升级 pi""升级 pi-web""升级完换 logo 重启""pi 升级到 X.Y.Z"时使用。
---

# pi / pi-web 升级流程

按固定顺序执行：**查 pi → 查 pi-web → 升级 → 换 logo → 重启服务 → 验证**。
顺序不能颠倒：pi-web 升级会覆盖 `public/icons` 和 `public/sw.js`，必须在升级之后再运行 logo 脚本。

## 关键路径

| 项目 | 路径 / 名称 |
|---|---|
| pi 全局安装 | `npm install -g` 默认前缀（由 Node 环境决定，可用 `npm prefix -g` 查看） |
| pi-web 安装目录 | `/opt/pi-web-npm/lib/node_modules/@agegr/pi-web` |
| pi-web 安装前缀 | `/opt/pi-web-npm` |
| logo 脚本 | `/root/bin/pi-web-set-logo.py`（默认源图 `/root/pi-agent.png`） |
| systemd 服务 | `pi-web.service`（端口 `30141`，监听 `127.0.0.1`） |

## 第 1 步：查 pi

```bash
pi --version                                              # 当前版本
npm view @earendil-works/pi-coding-agent version          # 最新版本
```

如用户指定了版本，以用户指定为准（例如 `1.6.0`）。当前版本已等于目标版本则跳过安装。

## 第 2 步：查 pi-web

```bash
grep '"version"' /opt/pi-web-npm/lib/node_modules/@agegr/pi-web/package.json   # 当前版本
npm view @agegr/pi-web version                                                  # 最新版本
```

同样以用户指定版本优先；已是目标版本则跳过安装。

## 第 3 步：升级

```bash
npm install -g @earendil-works/pi-coding-agent@<目标版本>
npm install -g --prefix /opt/pi-web-npm @agegr/pi-web@<目标版本>
```

验证：

```bash
pi --version
grep '"version"' /opt/pi-web-npm/lib/node_modules/@agegr/pi-web/package.json
node -e "require('/opt/pi-web-npm/lib/node_modules/@agegr/pi-web/node_modules/node-pty'); console.log('node-pty OK')"
```

注意：npm 通常会提示 `node-pty`、`@google/genai`、`protobufjs` 的 install script 被跳过。只要 `node-pty` 能加载就可以接受；如果加载失败，再用 `npm install -g --allow-scripts=...` 对应包重装。

## 第 4 步：换 logo

```bash
python3 /root/bin/pi-web-set-logo.py                 # 使用默认 /root/pi-agent.png
python3 /root/bin/pi-web-set-logo.py <图片路径>       # 指定其他图片
```

成功标志：输出含 `完成。` 且退出码为 0。脚本是幂等的，可以重复运行。

## 第 5 步：重启服务

```bash
systemctl restart pi-web.service
systemctl is-active pi-web.service                   # 应输出 active
```

## 第 6 步：验证

```bash
ps -eo pid,etime,args | grep -E "pi-web|next-server" | grep -v grep   # 新进程，etime 很短
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:30141/  # 307 为正常
```

## 汇报给用户

简要列出：pi 与 pi-web 的升级前后版本、logo 脚本是否成功、服务是否 active 且返回 HTTP 码。
如果浏览器仍显示旧图标，提示用户刷新，或在 DevTools 的 Application → Service Workers 中 Unregister 后再刷新。

## 出错处理

- 任一步失败时停止后续步骤，并报告具体错误，不要跳过。
- 不要用更大的模型或重试来掩盖安装失败，先看 npm 的错误输出。
- 服务起不来时，用 `journalctl -u pi-web.service -n 50 --no-pager` 查看日志。
