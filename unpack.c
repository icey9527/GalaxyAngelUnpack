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

// ȷ��Ŀ¼����
void ensure_directory_exists(const char* path) {
    char temp[1024];
    char* p = NULL;
    size_t len;
    
    strncpy(temp, path, sizeof(temp));
    len = strlen(temp);
    
    // ɾ��·��ĩβ��б��
    if (temp[len - 1] == '/' || temp[len - 1] == '\\') {
        temp[len - 1] = 0;
    }
    
    // �𼶴���Ŀ¼
    for (p = temp + 1; *p; p++) {
        if (*p == '/' || *p == '\\') {
            *p = 0;
            mkdir(temp, 0755);
            *p = '/';
        }
    }
    
    mkdir(temp, 0755);
}

// ���������
void unpack(const char* filename, const char* output_dir) {
    FILE* f = fopen(filename, "rb");
    if (!f) {
        printf("�޷����ļ�: %s\n", filename);
        return;
    }
    
    // ����ļ�ͷ
    char magic[6] = {0};
    fread(magic, 1, 5, f);
    if (strcmp(magic, "PIDX0") != 0) {
        printf("�ļ�ͷ����\n");
        fclose(f);
        return;
    }
    
    fseek(f, 0x8, SEEK_SET);
    if (read_int(f, -1) != 1) {
        printf("�ֵ�Ƥ�˹����ɲ��˶�idx�������\n");
        fclose(f);
        return;
    }
    
    // �������Ŀ¼
    ensure_directory_exists(output_dir);
    
    // ������־�ļ�
    FILE* log_file = fopen("unpack.log", "w");
    if (!log_file) {
        printf("�޷�������־�ļ�\n");
        fclose(f);
        return;
    }
    
    fprintf(log_file, "�ļ��У�\n");
    
    uint32_t start = read_int(f, 0xC);     // ������ʼ��ַ
    uint32_t IdxQ = read_int(f, 0x10);     // ����������
    uint32_t name_start = read_int(f, 0x20); // �ļ�����ʼ��ַ
    
    fprintf(log_file, "������ʼ��ַ��0x%x\n", start);
    fprintf(log_file, "������������%u\n", IdxQ);
    fprintf(log_file, "�ļ�����ʼ��ַ��0x%x\n\n", name_start);
    
    // ����JSONĿ¼
    char json_dir[1024];
    sprintf(json_dir, "%s/json", output_dir);
    ensure_directory_exists(json_dir);
    
    // ����JSON�ļ�
    char json_file[1024];
    sprintf(json_file, "%s/idx.json", json_dir);
    FILE* json_f = fopen(json_file, "w");
    if (!json_f) {
        printf("�޷�����JSON�ļ�\n");
        fclose(f);
        fclose(log_file);
        return;
    }
    
    // д��JSONͷ��
    fprintf(json_f, "{\n    \"start\": [\n        \"");
    
    // ����start���ֵ�ʮ����������
    unsigned char* start_data = (unsigned char*)malloc(start);
    fseek(f, 0, SEEK_SET);
    fread(start_data, 1, start, f);
    
    // ������������תΪʮ�������ַ���
    for (uint32_t i = 0; i < start; i++) {
        fprintf(json_f, "%02x", start_data[i]);
    }
    fprintf(json_f, "\"\n    ],\n    \"idx\": [\n");
    free(start_data);
    
    // ��ȡ��Ŀ��Ϣ
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
        printf("�ڴ����ʧ��\n");
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
    
    // ����ÿ����Ŀ
    for (uint32_t i = 0; i < IdxQ; i++) {
        // ��ȡ�ļ���
        fseek(f, entries[i].name_offset + name_start, SEEK_SET);
        char buffer[256] = {0};
        fread(buffer, 1, 255, f);
        
        // �����ַ���������
        int null_index = 0;
        while (buffer[null_index] && null_index < 255) {
            null_index++;
        }
        strncpy(entries[i].filename, buffer, null_index);
        
        // ��ȡ����
        fseek(f, entries[i].offset, SEEK_SET);
        unsigned char* data = (unsigned char*)malloc(entries[i].size);
        if (!data) {
            printf("�ڴ����ʧ��\n");
            continue;
        }
        fread(data, 1, entries[i].size, f);
        
        // JSON�ָ���
        if (i > 0) {
            fprintf(json_f, ",\n");
        }
        
        bool compstate = false;
        if (entries[i].type == 1) {
            // ��Ŀ¼
            count_folder++;
            fprintf(log_file, "%d: 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x %s\n", 
                count_folder, entries[i].type, entries[i].name_offset, 
                entries[i].sign, entries[i].offset, entries[i].uncompressed_size,
                entries[i].size, entries[i].filename);
            printf("%d: %s (Ŀ¼)\n", count_folder, entries[i].filename);
        } else {
            // ���ļ�
            count_file++;
            char output_path[1024];
            sprintf(output_path, "%s/%s", output_dir, entries[i].filename);
            
            // ȷ������ļ���Ŀ¼����
            char dir_path[1024];
            strcpy(dir_path, output_path);
            char* last_slash = strrchr(dir_path, '/');
            if (last_slash) {
                *last_slash = 0;
                ensure_directory_exists(dir_path);
            }
            
            // ���Խ�ѹ��
            compstate = uncompress(data, entries[i].size, output_path);
            if (!compstate) {
                // �����ѹʧ�ܣ�ֱ��д��ԭʼ����
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
        
        // д��JSON
        fprintf(json_f, "        [\"0x%x\", \"0x%x\", \"0x%x\", \"%s\", %s]", 
            entries[i].type, entries[i].sign, entries[i].offset, 
            entries[i].filename, compstate ? "true" : "false");
        
        free(data);
    }
    
    // ���JSON�ļ�
    fprintf(json_f, "\n    ]\n}");
    
    // �ͷ���Դ
    free(entries);
    fclose(f);
    fclose(log_file);
    fclose(json_f);
    
    printf("�����ɣ�\n");
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        printf("�÷���\n�����Ŀ���ļ� ���Ŀ¼\n");
        return 1;
    }
    
    // ����ļ���չ��
    char* ext = strrchr(argv[1], '.');
    if (ext && strcmp(ext, ".dat") == 0) {
        printf("Ŀ���ļ�: %s\n", argv[1]);
        unpack(argv[1], argv[2]);
    } else {
        printf("ֻ֧�ֽ��.dat�ļ�\n");
    }
    
    return 0;
}
