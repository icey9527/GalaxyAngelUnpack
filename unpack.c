#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <sys/stat.h>

#ifdef _WIN32
#include <direct.h>
#define mkdir(path, mode) _mkdir(path)
#endif

// 读取4字节整数（小端序）
uint32_t read_int(FILE* f, long address) {
    uint32_t value = 0;
    if (address >= 0) {
        fseek(f, address, SEEK_SET);
    }
    fread(&value, 4, 1, f);
    return value;
}

// 解压缩函数
bool uncompress(const unsigned char* data, size_t data_size, const char* output_file) {
    // 读取原始大小
    uint32_t param_2 = *(uint32_t*)(data + 4);  // 从文件中读取期待的原始大小
    
    // 初始化变量
    size_t param_4 = data_size;
    int iVar4 = 8;
    int iVar11 = 0;
    unsigned int uVar7 = 0xfee;
    unsigned int uVar10 = 0;
    unsigned char abStack_1020[0x1000];  // 缓冲区
    unsigned char bVar1 = 0;  // 添加这个变量声明
    unsigned char bVar2 = 0;  // 为安全起见也添加这个变量声明
    memset(abStack_1020, 0, sizeof(abStack_1020));
    
    // 输出数据存储
    unsigned char* uncompress_data = (unsigned char*)malloc(param_2);
    if (uncompress_data == NULL) {
        printf("内存分配失败\n");
        return false;
    }
    
    // 检查文件头，决定解压缩方式
    bool compstate = false;
    
    if (data_size > 3 && data[1] == '3' && data[2] == ';' && data[3] == '1') {
        // 使用控制字节的解压缩逻辑
        while (true) {
            while (true) {
                uVar10 >>= 1;
                unsigned int uVar6 = uVar10;
                if ((uVar10 & 0x100) == 0) {
                    if (param_4 <= iVar4) {
                        // 写出结果
                        FILE* f = fopen(output_file, "wb");
                        if (f) {
                            fwrite(uncompress_data, 1, iVar11, f);
                            fclose(f);
                        }
                        free(uncompress_data);
                        return true;
                    }
                    
                    unsigned char pbVar8 = data[iVar4];
                    iVar4++;
                    uVar10 = (pbVar8 ^ 0x72) | 0xff00;
                    uVar6 = pbVar8 ^ 0x72;
                }
                
                if ((uVar6 & 1) != 0) {
                    break;
                }
                
                if (param_4 <= iVar4 + 1) {
                    FILE* f = fopen(output_file, "wb");
                    if (f) {
                        fwrite(uncompress_data, 1, iVar11, f);
                        fclose(f);
                    }
                    free(uncompress_data);
                    return true;
                }
                
                int iVar9 = iVar4 + 1;
                unsigned char bVar1 = data[iVar4];
                iVar4 += 2;
                unsigned char bVar2 = data[iVar9];
                iVar9 = 0;
                
                // 循环解密
                while (iVar9 <= ((bVar2 ^ 0x72) & 0xf) + 2) {
                    uVar6 = (bVar1 ^ 0x72 | ((bVar2 ^ 0x72) & 0xf0) << 4) + iVar9;
                    iVar9++;
                    unsigned char bVar3 = abStack_1020[uVar6 & 0xfff];
                    if (iVar11 >= param_2) {  // 使用param_2作为解密数据的长度限制
                        break;
                    }
                    uncompress_data[iVar11] = bVar3;
                    abStack_1020[uVar7] = bVar3;
                    uVar7 = (uVar7 + 1) & 0xfff;
                    iVar11++;
                }
            }
            
            // 继续处理剩余的数据
            if (param_4 <= iVar4) {
                break;
            }
            
            bVar1 = data[iVar4];
            iVar4++;
            unsigned char uncompress_byte = bVar1 ^ 0x72;
            if (iVar11 >= param_2) {  // 使用param_2作为解密数据的长度限制
                break;
            }
            uncompress_data[iVar11] = uncompress_byte;
            abStack_1020[uVar7] = uncompress_byte;
            uVar7 = (uVar7 + 1) & 0xfff;
            iVar11++;
        }
    } 
    else if (data_size > 3 && data[1] == '3' && data[2] == ';' && data[3] == '0') {
        // 固定8字节处理的解压缩逻辑
        if (8 < param_4) {
            for (int i = 8; i < param_4; i++) {
                unsigned char uncompress_byte = data[i] ^ 0x72;
                if (iVar11 >= param_2) {
                    break;
                }
                uncompress_data[iVar11] = uncompress_byte;
                iVar11++;
            }
        }
    } 
    else {
        free(uncompress_data);
        return false; // 若文件头不匹配，就返回
    }
    
    // 写出最终的解密结果
    FILE* f = fopen(output_file, "wb");
    if (f) {
        fwrite(uncompress_data, 1, iVar11, f);
        fclose(f);
    }
    free(uncompress_data);
    return true;
}

// 确保目录存在
void ensure_directory_exists(const char* path) {
    char temp[1024];
    char* p = NULL;
    size_t len;
    
    strncpy(temp, path, sizeof(temp));
    len = strlen(temp);
    
    // 删除路径末尾的斜杠
    if (temp[len - 1] == '/' || temp[len - 1] == '\\') {
        temp[len - 1] = 0;
    }
    
    // 逐级创建目录
    for (p = temp + 1; *p; p++) {
        if (*p == '/' || *p == '\\') {
            *p = 0;
            mkdir(temp, 0755);
            *p = '/';
        }
    }
    
    mkdir(temp, 0755);
}

// 解包主函数
void unpack(const char* filename, const char* output_dir) {
    FILE* f = fopen(filename, "rb");
    if (!f) {
        printf("无法打开文件: %s\n", filename);
        return;
    }
    
    // 检查文件头
    char magic[6] = {0};
    fread(magic, 1, 5, f);
    if (strcmp(magic, "PIDX0") != 0) {
        printf("文件头不符\n");
        fclose(f);
        return;
    }
    
    fseek(f, 0x8, SEEK_SET);
    if (read_int(f, -1) != 1) {
        printf("又调皮了哈？可不兴对idx用这个啊\n");
        fclose(f);
        return;
    }
    
    // 创建输出目录
    ensure_directory_exists(output_dir);
    
    // 创建日志文件
    FILE* log_file = fopen("unpack.log", "w");
    if (!log_file) {
        printf("无法创建日志文件\n");
        fclose(f);
        return;
    }
    
    fprintf(log_file, "文件夹：\n");
    
    uint32_t start = read_int(f, 0xC);     // 索引起始地址
    uint32_t IdxQ = read_int(f, 0x10);     // 总索引数量
    uint32_t name_start = read_int(f, 0x20); // 文件名起始地址
    
    fprintf(log_file, "索引起始地址：0x%x\n", start);
    fprintf(log_file, "总索引数量：%u\n", IdxQ);
    fprintf(log_file, "文件名起始地址：0x%x\n\n", name_start);
    
    // 创建JSON目录
    char json_dir[1024];
    sprintf(json_dir, "%s/json", output_dir);
    ensure_directory_exists(json_dir);
    
    // 创建JSON文件
    char json_file[1024];
    sprintf(json_file, "%s/idx.json", json_dir);
    FILE* json_f = fopen(json_file, "w");
    if (!json_f) {
        printf("无法创建JSON文件\n");
        fclose(f);
        fclose(log_file);
        return;
    }
    
    // 写入JSON头部
    fprintf(json_f, "{\n    \"start\": [\n        \"");
    
    // 保存start部分的十六进制数据
    unsigned char* start_data = (unsigned char*)malloc(start);
    fseek(f, 0, SEEK_SET);
    fread(start_data, 1, start, f);
    
    // 将二进制数据转为十六进制字符串
    for (uint32_t i = 0; i < start; i++) {
        fprintf(json_f, "%02x", start_data[i]);
    }
    fprintf(json_f, "\"\n    ],\n    \"idx\": [\n");
    free(start_data);
    
    // 读取条目信息
    typedef struct {
        int index;
        uint32_t type;
        uint32_t name_offset;
        uint32_t sign;
        uint32_t offset;
        uint32_t uncompressed_size;
        uint32_t size;
        char filename[256];
    } Entry;
    
    Entry* entries = (Entry*)malloc(sizeof(Entry) * IdxQ);
    if (!entries) {
        printf("内存分配失败\n");
        fclose(f);
        fclose(log_file);
        fclose(json_f);
        return;
    }
    
    fseek(f, start, SEEK_SET);
    for (uint32_t i = 0; i < IdxQ; i++) {
        entries[i].index = i;
        entries[i].type = read_int(f, -1);
        entries[i].name_offset = read_int(f, -1);
        entries[i].sign = read_int(f, -1);
        entries[i].offset = read_int(f, -1);
        entries[i].uncompressed_size = read_int(f, -1);
        entries[i].size = read_int(f, -1);
    }
    
    int count_file = 0;
    int count_folder = 0;
    
    // 处理每个条目
    for (uint32_t i = 0; i < IdxQ; i++) {
    // 读取文件名
    fseek(f, entries[i].name_offset + name_start, SEEK_SET);
    memset(entries[i].filename, 0, sizeof(entries[i].filename));

    // 读取字符串直到null结束符
    int k = 0;
    char c;
    while (k < 255 && fread(&c, 1, 1, f) == 1 && c != '\0') {
        entries[i].filename[k++] = c;
    }
    entries[i].filename[k] = '\0';
        
        // 读取数据
        fseek(f, entries[i].offset, SEEK_SET);
        unsigned char* data = (unsigned char*)malloc(entries[i].size);
        if (!data) {
            printf("内存分配失败\n");
            continue;
        }
        fread(data, 1, entries[i].size, f);
        
        // JSON分隔符
        if (i > 0) {
            fprintf(json_f, ",\n");
        }
        
        bool compstate = false;
        if (entries[i].type == 1) {
            // 是目录
            count_folder++;
            fprintf(log_file, "%d: 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x %s\n", 
                count_folder, entries[i].type, entries[i].name_offset, 
                entries[i].sign, entries[i].offset, entries[i].uncompressed_size,
                entries[i].size, entries[i].filename);
            printf("%d: %s (目录)\n", count_folder, entries[i].filename);
        } else {
            // 是文件
            count_file++;
            char output_path[1024];
            sprintf(output_path, "%s/%s", output_dir, entries[i].filename);
            
            // 确保输出文件的目录存在
            char dir_path[1024];
            strcpy(dir_path, output_path);
            char* last_slash = strrchr(dir_path, '/');
            if (last_slash) {
                *last_slash = 0;
                ensure_directory_exists(dir_path);
            }
            
            // 尝试解压缩
            compstate = uncompress(data, entries[i].size, output_path);
            if (!compstate) {
                // 如果解压失败，直接写入原始数据
                FILE* out_f = fopen(output_path, "wb");
                if (out_f) {
                    fseek(f, entries[i].offset, SEEK_SET);
                    unsigned char* raw_data = (unsigned char*)malloc(entries[i].uncompressed_size);
                    if (raw_data) {
                        fread(raw_data, 1, entries[i].uncompressed_size, f);
                        fwrite(raw_data, 1, entries[i].uncompressed_size, out_f);
                        free(raw_data);
                    }
                    fclose(out_f);
                }
            }
            
            fprintf(log_file, "%d: 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x %s\n", 
                count_file, entries[i].type, entries[i].name_offset, 
                entries[i].sign, entries[i].offset, entries[i].uncompressed_size,
                entries[i].size, entries[i].filename);
            printf("%d: %s\n", count_file, entries[i].filename);
        }
        
        // 写入JSON
        fprintf(json_f, "        [\"0x%x\", \"0x%x\", \"0x%x\", \"%s\", %s]", 
            entries[i].type, entries[i].sign, entries[i].offset, 
            entries[i].filename, compstate ? "true" : "false");
        
        free(data);
    }
    
    // 完成JSON文件
    fprintf(json_f, "\n    ]\n}");
    
    // 释放资源
    free(entries);
    fclose(f);
    fclose(log_file);
    fclose(json_f);
    
    printf("解包完成！\n");
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        printf("用法：\n解包：目标文件 输出目录\n");
        return 1;
    }
    
    // 检查文件扩展名
    char* ext = strrchr(argv[1], '.');
    if (ext && strcmp(ext, ".dat") == 0) {
        printf("目标文件: %s\n", argv[1]);
        unpack(argv[1], argv[2]);
    } else {
        printf("只支持解包.dat文件\n");
    }
    
    return 0;
}
