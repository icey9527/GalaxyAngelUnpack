def make_file_id(lp_string):
    # 获取字符串长度并加1
    v1 = len(lp_string) + 1
    
    # 复制并转换字符串为小写
    string1 = lp_string.lower()
    
    # 初始化变量
    v2 = 0
    v3 = 0
    
    # 遍历字符串
    for i in range(len(string1)):
        v6 = ord(string1[i])
        
        # 累加字符的 ASCII 值
        v3 += v6
        
        # 计算 v2
        v2 = (v6 + (v2 << 8)) & 0xFFFFFFFF  # 保持 v2 为 32 位无符号整数
        
        # 检查 v2 是否需要取模
        if (v2 & 0xFF800000) != 0:
            v2 %= 0xFFF9D7
    
    # 返回最终的文件 ID
    return (v2 | (v3 << 24)) & 0xFFFFFFFF

# 测试函数
test_string = "B029.scn"
file_id = make_file_id(test_string)
print(f"The File ID for '{test_string}' is: {file_id}")