import os
import difflib
import re
from pycparser import parse_file

#比较text1和text2两个文本的字符串列表，并以统一的差异格式返回增量√
def text_diff(text1, text2):
    diff = difflib.unified_diff(text1.splitlines(), text2.splitlines())
    return "\n".join(diff)

#比较include和define等预处理命令差异√
def diff_preprocessing(text1, text2, file_name):
    diff_result = text_diff(text1,text2)
    if diff_result:
        with open(output_file, 'a', encoding='utf-8', errors='ignore') as f:
            f.write(f"Differences in preprocessing commands of {file_name}:\n")
            f.write(diff_result + "\n\n")

#比较函数之间差异√
def diff_function(text1, text2, name):
    diff_result = text_diff(text1, text2)
    if diff_result:
        with open(output_file, 'a', encoding='utf-8', errors='ignore') as f:
            f.write(f"Differences in {name}:\n")
            f.write(diff_result + "\n\n")

'''移除注释，保留纯代码部分√
def remove_annotations(code):
    lines = code.splitlines()
    code_without_annotations = []
    in_annotation_block = False
    #多行注释+单行注释
    for line in lines:
        if line.strip().startswith("/*"):   #多行注释：返回移除以/*开头的字符串
            in_annotation_block = True
        if not in_annotation_block:
            code_without_annotations.append(line)   #保存无注释纯代码
        if line.strip().endswith("*/"):
            in_annotation_block = False
        if line.strip().startswith("//"):   #单行注释
            continue
    return "\n".join(code_without_annotations)
'''

#移除注释，保留纯代码部分
def remove_annotations(code):
    # 使用正则表达式匹配单行和多行注释
    pattern = r"(\/\*[^*]*\*\/)|(\/\/.*$)"
    # 使用re.sub替换所有匹配的注释为空字符串
    no_comments_code = re.sub(pattern, "", code, flags=re.MULTILINE)
    return no_comments_code

#找函数定义的个数
def judge(node, count=0):
    for n in node:
        if (n.__class__.__name__=="FuncDef"):
            count+=1
    return count

#节点转为字符串进行比较，diff为1表示一致，小于1表示有差异
def node_to_txt(node1,node2):
    node_str1=str(node1)
    node_str2=str(node2)

    #用unified_diff、ndiff比较会出错，不知道怎么回事还是用SequenceMatcher吧
    diff=difflib.SequenceMatcher(None,node_str1.splitlines(),node_str2.splitlines()).quick_ratio()
    return diff

#分别遍历两个c程序的FileAST，找到差异所属的函数名
def traverse(node1, node2, num1=0, count1=0, num2=0, count2=0):
    #print(node.__class__.__name__)
    #修改（函数个数不变，仅内部变）
    for child1,child2 in zip(node1,node2):
        if child1.__class__.__name__=="FuncDef" and \
            child2.__class__.__name__=="FuncDef" and \
            num1<judge(node1,count1) and num2<judge(node2,count2):
            diff=node_to_txt(child1,child2)
            if diff<1:#有差异
                #print(f"差异来自函数：{child1.decl.name}")
                with open(output_file,'a',encoding='utf-8',errors='ignore') as f:
                    f.write(f"Differences in Function：{child1.decl.name}\n")
            else:
                continue
            num1+=1
            num2+=1
        else:
            traverse(child1,child2,num1,count1,num2,count2)

#对比两个版本目录下的同一文件√
def diff_file(file1, file2, output_file):
    #为了防止出现解码错误问题，加一个errors
    with open(file1, 'r', encoding='utf-8', errors='ignore') as f1, open(file2, 'r', encoding='utf-8', errors='ignore') as f2:
        code1 = f1.read()
        code2 = f2.read()
    # 移除注释，只保留代码部分
    code1 = remove_annotations(code1)
    #print(code1)
    code2 = remove_annotations(code2)
    diff_result = text_diff(code1, code2)
    if diff_result:
        with open(output_file, 'a', encoding='utf-8', errors='ignore') as f:
            f.write(f"Differences in {file1} and {file2}:\n")
            f.write(diff_result + "\n\n")

    ast1=parse_file(file1)
    ast2=parse_file(file2)
    traverse(ast1,ast2,0,0,0,0)


'''
    lines1 = code1.splitlines()
    lines2 = code2.splitlines()

    i, j = 0, 0
    count_left_curly_bracket1, count_right_curly_bracket1 = 0, 0  #统计左右花括号，得到完整函数体
    count_left_curly_bracket2, count_right_curly_bracket2 = 0, 0
    function_name = ""
    while i < len(lines1) and j < len(lines2):
        line1 = lines1[i]
        line2 = lines2[j]

        #待改，比较预处理命令
        if (line1.startswith("#include ") and line2.startswith("#include ")) or \
            (line1.startswith("#define ") and line2.startswith("#define "))or \
            (line1.startswith("#ifdef ") and line2.startswith("#ifdef "))or \
            (line1.startswith("#if ") and line2.startswith("#if "))or \
            (line1.startswith("#undef ") and line2.startswith("#undef ")):
            diff_preprocessing(line1, line2, file1)
            i += 1
            j += 1

        #比较函数√
        elif (line1.startswith("void ") and line2.startswith("void ")) or \
                (line1.startswith("int ") and line2.startswith("int ")) or \
                (line1.startswith("char ") and line2.startswith("char ")) or \
                (line1.startswith("double ") and line2.startswith("double ")) or \
                (line1.startswith("byte ") and line2.startswith("byte ")) or \
                (line1.startswith("bool ") and line2.startswith("bool ")) or \
                (line1.startswith("string ") and line2.startswith("string ")):
            function_name = line1.split()[1].split("(")[0]   #提取函数名【还要继续改，因为有的函数名在返回值类型下一行；并且需要判断这里是不是变量或者函数声明】
            function_lines1 = [line1]
            function_lines2 = [line2]
            #print(function_lines1)
            i += 1
            j += 1
            count_left_curly_bracket1 += 1
            count_left_curly_bracket2 += 1
            # 分别添加文件1、文件2对应某个方法的完整内容至method_lines1和method_lines2中
            while i < len(lines1) and not count_left_curly_bracket1 == count_right_curly_bracket1:#判定有错，暂时先这样
                if lines1[i].startswith("}"):
                    count_right_curly_bracket1 += 1
                function_lines1.append(lines1[i])
                i += 1

            while j < len(lines2) and not count_left_curly_bracket2 == count_right_curly_bracket2:
                if lines2[j].startswith("}"):
                    count_right_curly_bracket2 += 1
                function_lines2.append(lines2[j])
                j += 1

            diff_function("\n".join(function_lines1), "\n".join(function_lines2), f"{function_name}")
        else:
            i += 1
            j += 1
'''


#比较整个工程文件√
def diff_projects(project1, project2, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("")  # 清空文件内容，如果文件存在的话

    for root1, dirs1, files1 in os.walk(project1):  #os.walk走一遍目录，提取project1的起始路径root1、起始路径下的文件夹dirs1、起始路径下的文件files1
        for file1 in files1:
            if file1.endswith(".c"):    #还有.h文件没考虑
                file1_path = os.path.join(root1, file1)
                file2_path = os.path.join(project2, os.path.relpath(root1, project1), file1)    #找到file1的路径后，project2中相应位置文件用relpath找并join拼接
                if os.path.isfile(file2_path):
                    diff_file(file1_path, file2_path, output_file)
                else:
                    with open(output_file, 'a', encoding='utf-8', errors='ignore') as f:
                        f.write(f"{file2_path} does not exist in the second project\n")

    for root2, dirs2, files2 in os.walk(project2):
        for file2 in files2:
            if file2.endswith(".c"):
                file2_path = os.path.join(root2, file2)
                file1_path = os.path.join(project1, os.path.relpath(root2, project2), file2)
                if not os.path.isfile(file1_path):
                    with open(output_file, 'a', encoding='utf-8', errors='ignore') as f:
                        f.write(f"{file1_path} does not exist in the first project\n")




output_file = r"D:\研一\C文件差异\diffOut\CDiff1_2023919.txt"   # 存文件的地址
diff_projects(r'D:\研一\C文件差异\TCAS_mod\v1', r'D:\研一\C文件差异\TCAS_mod\v2', output_file) # 进行差异性分析的两个文件地址

#output_file = r"D:\研一\回归测试项目\学习\C差异分析\diffOutput\CDiff2.txt"   # 存文件的地址
#diff_projects(r'D:\研一\回归测试项目\学习\C差异分析\VIM\vim_1.0\vim\versions.alt\versions.orig\v1', r'D:\研一\回归测试项目\学习\C差异分析\VIM\vim_1.0\vim\versions.alt\versions.seeded\v1', output_file) # 进行差异性分析的两个文件地址

#output_file = r"D:\研一\回归测试项目\学习\C差异分析\diffOutput\CDiff3.txt"   # 存文件的地址
#diff_projects(r'D:\研一\回归测试项目\学习\C差异分析\SeaFile\seafile-client-5.1.4\seafile-client-5.1.4', r'D:\研一\回归测试项目\学习\C差异分析\SeaFile\seafile-client-6.2.4-testing\seafile-client-6.2.4-testing', output_file) # 进行差异性分析的两个文件地址