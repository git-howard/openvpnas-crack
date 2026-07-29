#!/usr/bin/env bash

set -e

cleanup() {
    if [ -d "egg_temp_working" ]; then
        rm -rf "egg_temp_working" 2>/dev/null || true
    fi
    if [ -f "uprop.py" ]; then
        rm -f "uprop.py"
    fi
    if [ -f "temp_egg.zip" ]; then
        rm -f "temp_egg.zip"
    fi
}

trap cleanup EXIT

DEFAULT_EGG_PATH="/usr/local/openvpn_as/lib/python/pyovpn-2.0-py3.12.egg"

read -p "请输入 egg 文件的路径和名称 [默认: ${DEFAULT_EGG_PATH}]: " USER_INPUT
EGG_PATH="${USER_INPUT:-$DEFAULT_EGG_PATH}"

if [ -z "$EGG_PATH" ]; then
    echo "错误: 未输入文件路径。"
    exit 1
fi

if [ ! -f "$EGG_PATH" ]; then
    echo "错误: 文件 '$EGG_PATH' 不存在。"
    exit 1
fi

TEMP_DIR="egg_temp_working"
if [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi

echo "正在解压 $EGG_PATH ..."
if ! unzip -q "$EGG_PATH" -d "$TEMP_DIR"; then
    echo "解压失败"
    exit 1
fi

TARGET_DIR="$TEMP_DIR/pyovpn/lic"
if [ ! -d "$TARGET_DIR" ]; then
    echo "错误: 在 egg 文件中未找到目标路径 pyovpn/lic"
    exit 1
fi

UPROP2_PATH="$TARGET_DIR/uprop2.pyc"
if [ -f "$UPROP2_PATH" ]; then
    echo "检测到 'uprop2.pyc' 已存在，跳过备份原文件步骤。"
else
    FOUND_ORIG=""
    for f in "$TARGET_DIR"/uprop.pyc "$TARGET_DIR"/uprop.*; do
        if [ -f "$f" ]; then
            FOUND_ORIG="$f"
            break
        fi
    done

    if [ -z "$FOUND_ORIG" ]; then
        echo "错误: 未在 pyovpn/lic 目录下找到原 uprop.pyc 文件。"
        exit 1
    fi

    cp "$FOUND_ORIG" "$UPROP2_PATH"
    echo "已成功将 pyovpn/lic 中的原文件复制并重命名生成 'uprop2.pyc'"
fi

read -p "请输入许可并发数量 (例如 100 或 1024): " LIC_INPUT
LIC_INPUT=$(echo "$LIC_INPUT" | xargs)

if ! [[ "$LIC_INPUT" =~ ^[0-9]+$ ]]; then
    echo "错误: 输入的许可数量必须是数字。"
    exit 1
fi

LIC_COUNT=$LIC_INPUT

cat <<PYEOF > uprop.py
from pyovpn.lic import uprop2

old_figure = None

def new_figure(self, licdict):
    ret = old_figure(self, licdict)
    ret['concurrent_connections'] = ${LIC_COUNT}
    return ret

for x in dir(uprop2):
    if x[:2] == '__':
        continue
    if x == 'UsageProperties':
        exec('old_figure = uprop2.UsageProperties.figure')
        exec('uprop2.UsageProperties.figure = new_figure')
    exec(f"{x} = uprop2.{x}")
PYEOF

DEST_UPROP_PYC="$TARGET_DIR/uprop.pyc"

if python3 -c "import py_compile; py_compile.compile('uprop.py', cfile='$DEST_UPROP_PYC', doraise=True)"; then
    echo "已成功将代码编译为 uprop.pyc (许可数量: ${LIC_COUNT}) 并写入 egg 的 pyovpn/lic 目录。"
else
    echo "编译 uprop.pyc 失败"
    exit 1
fi

echo "正在重新打包 egg 文件..."
EGG_ABS_PATH=$(python3 -c "import os, sys; print(os.path.abspath(sys.argv[1]))" "$EGG_PATH")
(cd "$TEMP_DIR" && zip -r -q "../temp_egg.zip" .)
mv temp_egg.zip "$EGG_ABS_PATH"

echo "完成！已成功更新并覆盖 egg 文件: $EGG_PATH"

echo "正在重启 OpenVPN AS 服务 (sudo systemctl restart openvpnas)..."
if sudo systemctl restart openvpnas; then
    echo "OpenVPN AS 服务重启成功！"
else
    echo "重启 OpenVPN AS 服务失败"
fi
