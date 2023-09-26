import os
import difflib
import re
import clang.cindex

from clang.cindex import Index
from clang.cindex import Config
from clang.cindex import CursorKind
from clang.cindex import TypeKind

from loguru import logger


class DiffParser():

    def get_diff_points(self, old_file: str, new_file: str) -> set:
        """
        比较旧版本文件和新版本文件，获取变更点
        :param old_file: 旧版本文件路径
        :param new_file: 新版本文件路径
        :return: 存储了变更点的集合，变更点的格式为: 文件路径?行号
        """
        old_lines = list()  # 存储旧版本文件内容
        new_lines = list()  # 存储新版本文件内容

        # 读取文件内容
        with open(old_file) as f:
            old_lines = f.readlines()
        with open(new_file) as f:
            new_lines = f.readlines()

        # 使用 difflib 进行差异分析
        d = difflib.Differ()
        diffs = d.compare(old_lines, new_lines)
        diff_points = set()

        # 遍历差异分析结果, 获取变更点
        line_num = 0
        for line in diffs:
            # 提取差异分析结果的前两个字符
            prefix = line[:2]

            # 更新行号
            if prefix in {"  ", "+ "}:
                line_num += 1

            # 若前两个字符为 " +" 将该行加入集合
            if prefix == "+ ":
                diff_points.add(os.path.abspath(new_file) + "?" + str(line_num))

        return diff_points

    def traverse(self, fn: str, node: clang.cindex.Cursor):
        """
        递归遍历AST
        :param fn:文件名
        :param node: AST节点
        :return:
        """
        for child in node.get_children():
            # 若当前节点不在变更点所在文件中, 跳过
            if child.location.file.name != fn:
                continue

            # 若当前节点的类型为 FUNCTION_DECL, 更新 now_func
            if child.kind == CursorKind.FUNCTION_DECL:
                self.now_func = child.spelling

            # 若当前节点的行在变更点所在行中, 将 now_func 加入 diff_funcs
            if child.location.line in self.dict_differences[fn]:
                self.diff_funcs.add(self.now_func)
                logger.debug(os.path.relpath(fn, __file__) + ", " + str(child.location.line) + ", " + self.now_func)

            # 递归遍历
            self.traverse(fn, child)

    def get_diff_funcs(self, diff_points: set) -> set:
        """
        获取变更点所在函数
        :param diff_points: 存储变更点的集合
        :return: 包含变更点的函数集合
        """
        # 获取 libclang.dll 的地址
        cmd_res = os.popen("where clang")
        clang_path = cmd_res.readlines()[0].rstrip("\n")
        libclang_path = os.path.join(os.path.dirname(clang_path), "libclang.dll")

        # 配置共享库
        if not Config.loaded:
            Config.set_library_file(libclang_path)

        # dict_differences 用于存储变更点信息
        # key 是文件名; value 是集合, 其中存储了变更点行号
        self.dict_differences = dict()

        # 遍历变更点集合, 更新字典
        for value in diff_points:
            lst_tmp = value.split("?")
            fn = lst_tmp[0]
            line = int(lst_tmp[1])

            if fn not in self.dict_differences.keys():
                self.dict_differences[fn] = set()
            self.dict_differences[fn].add(line)

        self.now_func = ""  # 当前遍历的函数
        self.diff_funcs = set()  # 存储包含变更点函数的集合

        # 解析包含变更点的文件, 根据AST确定变更点所在函数
        for fn in self.dict_differences.keys():
            index = Index.create()
            tu = index.parse(fn)  # Transition Units
            root = tu.cursor  # AST root node
            self.traverse(fn, root)

        # 返回包含变更点的集合
        return self.diff_funcs

    def diff_projects(self, project1: str, project2: str) -> dict:
        """
        比较两个版本目录文件夹下的.c程序差异
        :param project1: 旧版本程序文件夹
        :param project2: 新版本程序文件夹
        """
        # os.walk走一遍目录，提取project1的起始路径root1、起始路径下的文件夹dirs1、起始路径下的文件files1
        for root1, dirs1, files1 in os.walk(project1):
            for file1 in files1:
                if file1.endswith(".c"):  # 还有.h文件没考虑
                    file1_path = os.path.join(root1, file1)
                    file2_path = os.path.join(project2, os.path.relpath(root1, project1), file1)  # 找到file1的路径后，project2中相应位置文件用relpath找并join拼接
                    if os.path.isfile(file2_path):
                        df_p = self.get_diff_points(file1_path, file2_path)
                        df_f = self.get_diff_funcs(df_p)
                    else:
                        print(f"{file2_path} does not exist in the second project\n")


if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.abspath(__file__))
    old_project = os.path.join(root_dir, "test", "tcas", "versions.alt", "versions.orig", "v1")
    new_project = os.path.join(root_dir, "test", "tcas", "versions.alt", "versions.orig", "v2")

    dp = DiffParser()
    diff_info = dp.diff_projects(old_project, new_project)
    print(diff_info)
    del dp