#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include "cJSON.h"

#define XOR_KEY 0x72
#define BUFFER_SIZE (1024 * 1024) // 1MB缓冲区
// compress
#define WINDOW_SIZE 4096
#define MAX_MATCH_LEN 18
#define MIN_MATCH_LEN 3

typedef struct {
    uint8_t data[WINDOW_SIZE];
    int pos;
    int size;
} SlidingWindow;

void window_init(SlidingWindow* window);
void window_update(SlidingWindow* window, uint8_t byte);
int find_match(SlidingWindow* window, uint8_t* input, int cursor, int end, int* distance);
uint32_t compress(uint8_t* input, uint32_t input_size, uint8_t** output);


// 滑动窗口初始化
void window_init(SlidingWindow* window) {
    memset(window->data, 0, WINDOW_SIZE);
    window->pos = 0xFEE;
    window->size = 0;
}

// 更新滑动窗口
void window_update(SlidingWindow* window, uint8_t byte) {
    window->data[window->pos] = byte;
    window->pos = (window->pos + 1) % WINDOW_SIZE;
    if (window->size < WINDOW_SIZE) window->size++;
}

// 查找匹配
int find_match(SlidingWindow* window, uint8_t* input, int cursor, int end, int* distance) {
    int max_len = 0;
    int max_pos = 0;
    int search_start = (cursor >= (WINDOW_SIZE - 8)) ? (cursor - (WINDOW_SIZE - 8)) : 0;
    
    for (int i = search_start; i < cursor; i++) {
        int len = 0;
        while (len < MAX_MATCH_LEN && 
               i + len < cursor && 
               cursor + len < end && 
               input[i + len] == input[cursor + len]) {
            len++;
        }
        if (len > max_len) {
            max_len = len;
            max_pos = i;
        }
    }
    
    *distance = (window->pos - (cursor - max_pos)) % WINDOW_SIZE;
    return (max_len >= MIN_MATCH_LEN) ? max_len : 0;
}

// 主压缩函数 - 完全基于内存
uint32_t compress(uint8_t* input, uint32_t input_size, uint8_t** output) {
    // 预估最大输出大小 (输入大小 * 1.5 + 8)
    uint32_t max_output_size = input_size + (input_size / 2) + 8;
    *output = malloc(max_output_size);
    if (!*output) return 0;
    
    // 写入头部魔数和原始大小
    memcpy(*output, "\x20\x33\x3B\x31", 4);
    *((uint32_t*)(*output + 4)) = input_size;
    
    SlidingWindow window;
    window_init(&window);
    
    int read_pos = 0;
    int output_pos = 8;
    uint8_t control_mask = 0;
    int control_bit = 0;
    uint8_t data_buffer[16];
    int data_buffer_len = 0;
    
    while (read_pos < input_size) {
        int distance, match_len = 0;
        if (window.size >= MIN_MATCH_LEN) {
            match_len = find_match(&window, input, read_pos, input_size, &distance);
        }
        
        if (match_len >= MIN_MATCH_LEN) {
            control_mask |= (0 << control_bit);
            
            uint8_t byte1 = distance & 0xFF;
            uint8_t byte2 = ((distance >> 4) & 0xF0) | ((match_len - 3) & 0x0F);
            
            data_buffer[data_buffer_len++] = byte1 ^ XOR_KEY;
            data_buffer[data_buffer_len++] = byte2 ^ XOR_KEY;
            
            for (int i = 0; i < match_len; i++) {
                window_update(&window, input[read_pos + i]);
            }
            read_pos += match_len;
        } else {
            control_mask |= (1 << control_bit);
            
            uint8_t value = input[read_pos];
            data_buffer[data_buffer_len++] = value ^ XOR_KEY;
            
            window_update(&window, value);
            read_pos++;
        }
        control_bit++;
        
        if (control_bit >= 8) {
            uint8_t ctrl_byte = control_mask ^ XOR_KEY;
            (*output)[output_pos++] = ctrl_byte;
            memcpy(*output + output_pos, data_buffer, data_buffer_len);
            output_pos += data_buffer_len;
            
            control_mask = 0;
            control_bit = 0;
            data_buffer_len = 0;
        }
    }
    
    if (control_bit != 0) {
        while (control_bit < 8) {
            control_mask |= (0 << control_bit);
            control_bit++;
        }
        uint8_t ctrl_byte = control_mask ^ XOR_KEY;
        (*output)[output_pos++] = ctrl_byte;
        memcpy(*output + output_pos, data_buffer, data_buffer_len);
        output_pos += data_buffer_len;
    }
    
    // 重新调整输出缓冲区大小
    *output = realloc(*output, output_pos);
    return output_pos;
}


// compress end

typedef struct {
    uint32_t type;
    uint32_t name_offset;
    uint32_t sign;
    uint32_t offset;
    uint32_t uncompressed_size;
    uint32_t size;
    char filename[256];
    bool compressed;
} IndexEntry;

uint32_t parse_hex(const char* str) {
    return (uint32_t)strtoul(str, NULL, 16);
}

void process_index_entry(cJSON* item, IndexEntry* entry) {
    cJSON* type = cJSON_GetArrayItem(item, 0);
    cJSON* sign = cJSON_GetArrayItem(item, 1);
    cJSON* offset = cJSON_GetArrayItem(item, 2);
    cJSON* filename = cJSON_GetArrayItem(item, 3);
    cJSON* compressed = cJSON_GetArrayItem(item, 4);

    entry->type = parse_hex(type->valuestring);
    entry->sign = parse_hex(sign->valuestring);
    entry->offset = parse_hex(offset->valuestring);
    strncpy(entry->filename, filename->valuestring, 255);
    entry->compressed = cJSON_IsTrue(compressed);
}

void compress_data(unsigned char** data, uint32_t* size) {
    uint8_t* compressed_data = NULL;
    uint32_t compressed_size = compress(*data, *size, &compressed_data);
    
    if (compressed_data && compressed_size < *size) {
        free(*data);
        *data = compressed_data;
        *size = compressed_size;
    } else if (compressed_data) {
        // 如果压缩后大小没有变小，保持原样
        free(compressed_data);
    }
}


void pack(const char* input_dir, const char* output_file, const char* index_file) {
    // 1. 读取 idx.json
    FILE* json_fp = fopen(index_file, "rb");
    fseek(json_fp, 0, SEEK_END);
    long json_size = ftell(json_fp);
    fseek(json_fp, 0, SEEK_SET);
    char* json_buffer = malloc(json_size + 1);
    fread(json_buffer, 1, json_size, json_fp);
    json_buffer[json_size] = 0;
    fclose(json_fp);

    cJSON* root = cJSON_Parse(json_buffer);
    free(json_buffer);

    // 2. 解析 start 区（十六进制数据）
    cJSON* start = cJSON_GetObjectItem(root, "start");
    char* hex_str = cJSON_GetArrayItem(start, 0)->valuestring;
    uint32_t hex_len = strlen(hex_str);
    unsigned char* bin_data = malloc(hex_len / 2);
    for (uint32_t i = 0; i < hex_len; i += 2) {
        char byte_str[3] = { hex_str[i], hex_str[i + 1], 0 };
        bin_data[i / 2] = (unsigned char)strtoul(byte_str, NULL, 16);
    }

    // 3. 打开输出文件
    FILE* dat = fopen(output_file, "wb");
    if (!dat) {
        printf("无法创建输出文件: %s\n", output_file);
        return;
    }

    // 4. 写入 start 区
    fwrite(bin_data, 1, hex_len / 2, dat);
    uint32_t name_table_offset = *(uint32_t*)(bin_data + 0x20);
    free(bin_data);

    // 5. 计算索引表大小（每个条目 24 字节）
    cJSON* idx = cJSON_GetObjectItem(root, "idx");
    int entry_count = cJSON_GetArraySize(idx);
    uint32_t index_table_size = entry_count * 24;

    // 6. 写入空的索引表（占位，稍后填充）
    unsigned char* zero_buffer = calloc(index_table_size, 1);
    fwrite(zero_buffer, 1, index_table_size, dat);
    free(zero_buffer);

    // 7. 写入文件名表，并记录 name_offset
    
    uint32_t current_name_offset = 0;

    for (int i = 0; i < entry_count; i++) {
        IndexEntry entry;
        process_index_entry(cJSON_GetArrayItem(idx, i), &entry);

        // 写入文件名（带 \0）
        fseek(dat, name_table_offset + current_name_offset, SEEK_SET);
        fwrite(entry.filename, 1, strlen(entry.filename) + 1, dat);

        // 更新索引表的 name_offset
        fseek(dat, hex_len / 2 + (i * 24) + 4, SEEK_SET); // 跳到 name_offset 位置
        fwrite(&current_name_offset, 4, 1, dat);
        printf("%s: %u\n",entry.filename, name_table_offset +current_name_offset);

        current_name_offset += strlen(entry.filename) + 1;
    }

    // 8. 填充索引表的其他字段（type, sign, offset, size等）
    for (int i = 0; i < entry_count; i++) {
        IndexEntry entry;
        process_index_entry(cJSON_GetArrayItem(idx, i), &entry);

        // 跳到当前索引条目的起始位置
        fseek(dat, hex_len / 2 + (i * 24), SEEK_SET);

        // 依次写入 type, name_offset, sign, offset, uncompressed_size, size
        fwrite(&entry.type, 4, 1, dat);
        // name_offset 已经在步骤7写入
        fseek(dat, 4, SEEK_CUR); // 跳过已写入的 name_offset
        fwrite(&entry.sign, 4, 1, dat);
        fwrite(&entry.offset, 4, 1, dat);
        fwrite(&entry.uncompressed_size, 4, 1, dat);
        fwrite(&entry.size, 4, 1, dat);
    }

// 9. 写入文件数据
for (int i = 0; i < entry_count; i++) {
    IndexEntry entry;
    process_index_entry(cJSON_GetArrayItem(idx, i), &entry);

    if (entry.type == 1) continue; // 跳过目录

    char filepath[1024];
    snprintf(filepath, sizeof(filepath), "%s/%s", input_dir, entry.filename);

    FILE* src = fopen(filepath, "rb");
    if (!src) {
        printf("无法打开文件: %s\n", filepath);
        continue;
    }

    setvbuf(src, NULL, _IOFBF, BUFFER_SIZE);

    fseek(src, 0, SEEK_END);
    uint32_t file_size = ftell(src);
    fseek(src, 0, SEEK_SET);

    unsigned char* buffer = malloc(file_size);
    fread(buffer, 1, file_size, src);
    fclose(src);

    uint32_t original_size = file_size;
    if (entry.compressed) {
        compress_data(&buffer, &file_size);
    }

    // 更新索引表中的大小信息
    entry.uncompressed_size = original_size;  // 原始大小
    entry.size = file_size;                   // 实际大小(压缩或未压缩)

    // 将更新后的大小信息写回索引表
    fseek(dat, hex_len / 2 + (i * 24) + 16, SEEK_SET); // 定位到uncompressed_size字段
    fwrite(&entry.uncompressed_size, 4, 1, dat);
    fseek(dat, hex_len / 2 + (i * 24) + 20, SEEK_SET); // 定位到size字段
    fwrite(&entry.size, 4, 1, dat);

    // 写入文件数据
    fseek(dat, entry.offset, SEEK_SET);
    fwrite(buffer, 1, entry.size, dat);
    free(buffer);

    // 打印信息
    printf("文件: %s, 原始大小: %u, 存储大小: %u, 压缩: %s\n",
           entry.filename, entry.uncompressed_size, entry.size,
           entry.compressed ? "是" : "否");
}

// 10. 关闭文件和释放内存
fclose(dat);
cJSON_Delete(root);
printf("打包完成: %s\n", output_file);

}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        printf("用法: %s 输入目录 输出文件.dat\n", argv[0]);
        return 1;
    }
    char index_file[1024];
    snprintf(index_file, sizeof(index_file), "%s/json/idx.json", argv[1]);
    pack(argv[1], argv[2], index_file);
    return 0;
}
