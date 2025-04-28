#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>
#include <stdint.h>
#include <stdbool.h> 
#include <io.h> 
#include "cJSON.h"



typedef struct {
    uint32_t name_offset;
    uint32_t offset;
    uint32_t uncompressSize;
    uint32_t size;
} FSTSEntry;

// ��ȡ4�ֽ�������С����
uint32_t read_int(FILE* f, long address) {
    uint32_t value = 0;
    if (address >= 0) {
        fseek(f, address, SEEK_SET);
    }
    fread(&value, 4, 1, f);
    return value;
}

// ��ѹ������
bool uncompress(const unsigned char* data, size_t data_size, const char* output_file) {
    // ��ȡԭʼ��С
    uint32_t param_2 = *(uint32_t*)(data + 4);  // ���ļ��ж�ȡ�ڴ���ԭʼ��С
    
    // ��ʼ������
    size_t param_4 = data_size;
    int iVar4 = 8;
    int iVar11 = 0;
    unsigned int uVar7 = 0xfee;
    unsigned int uVar10 = 0;
    unsigned char abStack_1020[0x1000];  // ������
    unsigned char bVar1 = 0;  // ��������������
    unsigned char bVar2 = 0;  // Ϊ��ȫ���Ҳ��������������
    memset(abStack_1020, 0, sizeof(abStack_1020));
    
    // ������ݴ洢
    unsigned char* uncompress_data = (unsigned char*)malloc(param_2);
    if (uncompress_data == NULL) {
        printf("�ڴ����ʧ��\n");
        return false;
    }
    
    // ����ļ�ͷ��������ѹ����ʽ
    bool compstate = false;
    
    if (data_size > 3 && data[1] == '3' && data[2] == ';' && data[3] == '1') {
        // ʹ�ÿ����ֽڵĽ�ѹ���߼�
        while (true) {
            while (true) {
                uVar10 >>= 1;
                unsigned int uVar6 = uVar10;
                if ((uVar10 & 0x100) == 0) {
                    if (param_4 <= iVar4) {
                        // д�����
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
                
                // ѭ������
                while (iVar9 <= ((bVar2 ^ 0x72) & 0xf) + 2) {
                    uVar6 = (bVar1 ^ 0x72 | ((bVar2 ^ 0x72) & 0xf0) << 4) + iVar9;
                    iVar9++;
                    unsigned char bVar3 = abStack_1020[uVar6 & 0xfff];
                    if (iVar11 >= param_2) {  // ʹ��param_2��Ϊ�������ݵĳ�������
                        break;
                    }
                    uncompress_data[iVar11] = bVar3;
                    abStack_1020[uVar7] = bVar3;
                    uVar7 = (uVar7 + 1) & 0xfff;
                    iVar11++;
                }
            }
            
            // ��������ʣ�������
            if (param_4 <= iVar4) {
                break;
            }
            
            bVar1 = data[iVar4];
            iVar4++;
            unsigned char uncompress_byte = bVar1 ^ 0x72;
            if (iVar11 >= param_2) {  // ʹ��param_2��Ϊ�������ݵĳ�������
                break;
            }
            uncompress_data[iVar11] = uncompress_byte;
            abStack_1020[uVar7] = uncompress_byte;
            uVar7 = (uVar7 + 1) & 0xfff;
            iVar11++;
        }
    } 
    else if (data_size > 3 && data[1] == '3' && data[2] == ';' && data[3] == '0') {
        // �̶�8�ֽڴ���Ľ�ѹ���߼�
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
        return false; // ���ļ�ͷ��ƥ�䣬�ͷ���
    }
    
    // д�����յĽ��ܽ��
    FILE* f = fopen(output_file, "wb");
    if (f) {
        fwrite(uncompress_data, 1, iVar11, f);
        fclose(f);
    }
    free(uncompress_data);
    return true;
}

// ���������������༶Ŀ¼
void mkdir_p(const char *dir) {
    char tmp[MAX_PATH];
    char *p = NULL;
    size_t len;

    snprintf(tmp, sizeof(tmp), "%s", dir);
    len = strlen(tmp);
    if (tmp[len - 1] == '/')
        tmp[len - 1] = 0;
    for (p = tmp + 1; *p; p++)
        if (*p == '/') {
            *p = 0;
            mkdir(tmp);
            *p = '/';
        }
    mkdir(tmp);
}

char* read_string(FILE* f, long offset) {
    long current = ftell(f);
    fseek(f, offset, SEEK_SET);
    
    char* buffer = malloc(256);
    int i = 0;
    while (1) {
        char c;
        if (fread(&c, 1, 1, f) != 1) break;
        if (c == 0 || feof(f)) break;
        buffer[i++] = c;
    }
    buffer[i] = '\0';
    
    fseek(f, current, SEEK_SET);
    return buffer;
}

void write_output(const char* output_dir, const char* filename, const unsigned char* data, size_t size) {
    char path[MAX_PATH];
    snprintf(path, MAX_PATH, "%s/%s", output_dir, filename);
    mkdir_p(output_dir);
    
    FILE* f = fopen(path, "wb");
    if (f) {
        fwrite(data, 1, size, f);
        fclose(f);
    }
}

cJSON* process_fsts(FILE* f, const char* output_dir) {
    char magic[5] = {0};
    fread(magic, 1, 4, f);
    if (strcmp(magic, "FSTS") != 0) {
        printf("Invalid FSTS header\n");
        return NULL;
    }

    uint32_t IdxQ = read_int(f, -1);
    uint32_t start = read_int(f, -1);
    uint32_t name_start = read_int(f, -1);

    FSTSEntry* entries = malloc(IdxQ * sizeof(FSTSEntry));
    fseek(f, start, SEEK_SET);
    
    for (uint32_t i = 0; i < IdxQ; i++) {
        entries[i].name_offset = read_int(f, -1);
        entries[i].offset = read_int(f, -1);
        entries[i].size = read_int(f, -1);
        entries[i].uncompressSize = read_int(f, -1);
    }

    cJSON* rebuild = cJSON_CreateObject();
    for (uint32_t i = 0; i < IdxQ; i++) {
        char* name = read_string(f, name_start + entries[i].name_offset);
        char* filename = strrchr(name, '/');
        filename = filename ? filename + 1 : name;

        unsigned char* data = malloc(entries[i].size);
        fseek(f, entries[i].offset, SEEK_SET);
        fread(data, 1, entries[i].size, f);

        char path[MAX_PATH];
        snprintf(path, MAX_PATH, "%s/%s", output_dir, filename);
        
        if (!uncompress(data, entries[i].size, path)) {
            write_output(output_dir, filename, data, entries[i].size);
        }

        cJSON_AddStringToObject(rebuild, filename, name);
        free(data);
        free(name);
    }

    free(entries);
    return rebuild;
}

void process_pidx0(const char* filename, const char* output_dir) {
    FILE* f = fopen(filename, "rb");
    if (!f) return;

    char magic[5] = {0};
    fread(magic, 1, 4, f);
    if (strcmp(magic, "PIDX") != 0) {
        printf("Invalid PIDX header\n");
        fclose(f);
        return;
    }

    if (read_int(f, 0x8) != 1) {
        printf("Invalid IDX file\n");
        fclose(f);
        return;
    }

    cJSON* list = cJSON_CreateObject();
    
    uint32_t start = read_int(f, 0xC);

    fseek(f, 0, SEEK_SET);
    unsigned char* start_data = malloc(start);
    fread(start_data, 1, start, f);
    char* hex_str = malloc(start * 2 + 1);
    for (int i = 0; i < start; i++) {
        sprintf(hex_str + i*2, "%02x", start_data[i]);
    }
    cJSON_AddStringToObject(list, "start", hex_str); // ��ӵ�JSON����
    free(start_data);
    free(hex_str);

    uint32_t IdxQ = read_int(f, 0x10);
    uint32_t name_start = read_int(f, 0x20);
    uint32_t sub_index_count = read_int(f, 0x50);

    uint32_t* sub_index_pointers = malloc(sub_index_count * sizeof(uint32_t));
    uint32_t sub_index_start = start + 4;
    for (uint32_t i = 0; i < sub_index_count; i++) {
        fseek(f, sub_index_start + i*4, SEEK_SET);
        uint32_t pointer = read_int(f, -1);
        sub_index_pointers[i] = pointer + start;
    }

    
    for (uint32_t i = 0; i < sub_index_count; i++) {
        fseek(f, sub_index_pointers[i], SEEK_SET);
        uint32_t name_offset = read_int(f, -1);
        /* uint32_t placeholder = */ read_int(f, -1);
        uint32_t fst_offset = read_int(f, -1);
        uint32_t fst_size = read_int(f, -1);
        /* uint32_t num = */ read_int(f, -1);

        char* name = read_string(f, name_start + name_offset);
        printf("Processing: %s\n", name);
        
        fseek(f, fst_offset, SEEK_SET);
        unsigned char* fst_data = malloc(fst_size);
        fread(fst_data, 1, fst_size, f);

        char sub_output[MAX_PATH];
        snprintf(sub_output, MAX_PATH, "%s/%s", output_dir, name);
        mkdir_p(sub_output);
        
        FILE* tmp_f = tmpfile();
        fwrite(fst_data, 1, fst_size, tmp_f);
        rewind(tmp_f);
        
        cJSON* sub_list = process_fsts(tmp_f, sub_output);
        cJSON_AddItemToObject(list, name, sub_list);
        
        fclose(tmp_f);
        free(fst_data);
        free(name);
    }

    char list_path[MAX_PATH];
    snprintf(list_path, MAX_PATH, "%s/list.json", output_dir);
    FILE* json_file = fopen(list_path, "w");
    if (json_file) {
        char* json_str = cJSON_Print(list);
        fwrite(json_str, 1, strlen(json_str), json_file);
        free(json_str);
        fclose(json_file);
    }

    free(sub_index_pointers);
    cJSON_Delete(list);
    fclose(f);
}

int main(int argc, char** argv) {
    if (argc < 3) {
        printf("Usage: %s <input.dat/.fsts> <output_dir>\n", argv[0]);
        return 1;
    }

    const char* input = argv[1];
    const char* output = argv[2];

    struct stat path_stat;
    stat(input, &path_stat);

    if (S_ISREG(path_stat.st_mode)) {
        const char* ext = strrchr(input, '.');
        if (ext && strcasecmp(ext, ".dat") == 0) {
            process_pidx0(input, output);
        } else if (ext && strcasecmp(ext, ".fsts") == 0) {
            FILE* f = fopen(input, "rb");
            if (f) {
                process_fsts(f, output);
                fclose(f);
            }
        } else {
            printf("Unsupported file type\n");
        }
    } else {
        printf("Input path does not exist or is not a file\n");
    }

    return 0;
}