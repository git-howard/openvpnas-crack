import zipfile
import os
import shutil
import py_compile
import subprocess

def main():
    # 默认 egg 文件的路径
    default_egg_path = "/usr/local/openvpn_as/lib/python/pyovpn-2.0-py3.12.egg"
    
    # 提示用户输入 egg 文件的路径和名称，若直接回车则使用默认值
    user_input = input(f"请输入 egg 文件的路径和名称 [默认: {default_egg_path}]: ").strip()
    egg_path = user_input if user_input else default_egg_path
    
    if not egg_path:
        print("错误: 未输入文件路径。")
        return

    if not os.path.exists(egg_path):
        print(f"错误: 文件 '{egg_path}' 不存在。")
        return

    temp_dir = 'egg_temp_working'
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    print(f"正在解压 {egg_path} ...")
    try:
        with zipfile.ZipFile(egg_path, 'r') as zf:
            zf.extractall(temp_dir)
    except Exception as e:
        print(f"解压失败: {e}")
        return

    # 目标路径：./pyovpn/lic
    target_dir = os.path.join(temp_dir, 'pyovpn', 'lic')
    if not os.path.exists(target_dir):
        print(f"错误: 在 egg 文件中未找到目标路径 pyovpn/lic")
        shutil.rmtree(temp_dir)
        return

    # 检查 pyovpn/lic 下是否已存在 uprop2.pyc
    uprop2_path = os.path.join(target_dir, 'uprop2.pyc')
    if os.path.exists(uprop2_path):
        print("检测到 'uprop2.pyc' 已存在，跳过备份原文件步骤。")
    else:
        # 在 egg 文件的 pyovpn/lic 目录下寻找原 uprop.pyc 文件（或 uprop. 开头的文件）
        files = os.listdir(target_dir)
        found_orig_file = None
        for f in files:
            if f == 'uprop.pyc' or f.startswith('uprop.'):
                found_orig_file = f
                break

        if not found_orig_file:
            print("错误: 未在 pyovpn/lic 目录下找到原 uprop.pyc 文件。")
            shutil.rmtree(temp_dir)
            return

        # 将原 uprop.pyc 复制并重命名为 uprop2.pyc
        orig_uprop_path = os.path.join(target_dir, found_orig_file)
        shutil.copy(orig_uprop_path, uprop2_path)
        print(f"已成功将 pyovpn/lic 中的原 '{found_orig_file}' 复制并重命名生成 'uprop2.pyc'")

    # 询问许可并发数量，并编译生成 uprop.pyc 放到 egg 文件的 pyovpn/lic 目录里
    lic_input = input("请输入许可并发数量 (例如 100 或 1024): ").strip()
    if not lic_input.isdigit():
        print("错误: 输入的许可数量必须是数字。")
        shutil.rmtree(temp_dir)
        return
    
    lic_count = int(lic_input)

    py_code = f"""from pyovpn.lic import uprop2

old_figure = None

def new_figure(self, licdict):
    ret = old_figure(self, licdict)
    ret['concurrent_connections'] = {lic_count}
    return ret

for x in dir(uprop2):
    if x[:2] == '__':
        continue
    if x == 'UsageProperties':
        exec('old_figure = uprop2.UsageProperties.figure')
        exec('uprop2.UsageProperties.figure = new_figure')
    exec(f"{{x}} = uprop2.{{x}}")
"""

    local_py_path = "uprop.py"
    with open(local_py_path, "w", encoding="utf-8") as f:
        f.write(py_code)

    dest_uprop_pyc = os.path.join(target_dir, "uprop.pyc")
    try:
        py_compile.compile(local_py_path, cfile=dest_uprop_pyc, doraise=True)
        print(f"已成功将代码编译为 uprop.pyc (许可数量: {lic_count}) 并写入 egg 的 pyovpn/lic 目录。")
    except Exception as e:
        print(f"编译 uprop.pyc 失败: {e}")
        shutil.rmtree(temp_dir)
        return

    # 重新打包为 egg 覆盖原文件
    print("正在重新打包 egg 文件...")
    with zipfile.ZipFile(egg_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files_in_dir in os.walk(temp_dir):
            for file in files_in_dir:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, temp_dir)
                zf.write(full_path, rel_path)

    shutil.rmtree(temp_dir)
    print(f"完成！已成功更新并覆盖 egg 文件: {egg_path}")

    # 重启 OpenVPN AS 服务
    print("正在重启 OpenVPN AS 服务 (sudo systemctl restart openvpnas)...")
    try:
        subprocess.run(["sudo", "systemctl", "restart", "openvpnas"], check=True)
        print("OpenVPN AS 服务重启成功！")
    except subprocess.CalledProcessError as e:
        print(f"重启 OpenVPN AS 服务失败: {e}")

if __name__ == '__main__':
    main()
