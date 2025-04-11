#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#pragma pack(push, 1)
typedef struct {
    uint8_t header[0x14];
    uint32_t width;   // 小端序 0x14-0x17
    uint32_t height;  // 小端序 0x18-0x1B
    uint8_t bpp_flag; // 0x24
} TexHeader;
#pragma pack(pop)

uint32_t read_le32(const uint8_t* data) {
    return data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24);
}

// 16bpp转换
uint8_t* convert_16bpp(const uint8_t* data, uint32_t width, uint32_t height) {
    uint8_t* rgb_data = (uint8_t*)malloc(width * height * 3);
    const uint8_t* pixel_data = data + 0x40;

    for (uint32_t y = 0; y < height; y++) {
        for (uint32_t x = 0; x < width; x++) {
            uint32_t pos = (y * width + x) * 2;
            if (pos + 2 > width * height * 2) break;

            uint16_t pixel = *(uint16_t*)(pixel_data + pos);
            uint8_t r = (pixel & 0x1F) << 3;
            uint8_t g = ((pixel >> 5) & 0x1F) << 3;
            uint8_t b = ((pixel >> 10) & 0x1F) << 3;

            rgb_data[(y * width + x) * 3] = r | (r >> 5);
            rgb_data[(y * width + x) * 3 + 1] = g | (g >> 5);
            rgb_data[(y * width + x) * 3 + 2] = b | (b >> 5);
        }
    }
    return rgb_data;
}

// 24bpp转换
uint8_t* convert_24bpp(const uint8_t* data, uint32_t width, uint32_t height) {
    uint8_t* rgb_data = (uint8_t*)malloc(width * height * 3);
    const uint8_t* pixel_data = data + 0x50;

    for (uint32_t y = 0; y < height; y++) {
        for (uint32_t x = 0; x < width; x++) {
            uint32_t pos = (y * width + x) * 3;
            if (pos + 3 > width * height * 3) break;

            rgb_data[(y * width + x) * 3] = pixel_data[pos];
            rgb_data[(y * width + x) * 3 + 1] = pixel_data[pos + 1];
            rgb_data[(y * width + x) * 3 + 2] = pixel_data[pos + 2];
        }
    }
    return rgb_data;
}

int process_tex(const char* input_path, const char* output_folder) {
    FILE* fp = fopen(input_path, "rb");
    if (!fp) return 0;

    fseek(fp, 0, SEEK_END);
    long size = ftell(fp);
    rewind(fp);

    uint8_t* data = (uint8_t*)malloc(size);
    fread(data, 1, size, fp);
    fclose(fp);

    if (size < 0x25) {
        printf("文件太小\n");
        free(data);
        return 0;
    }

    TexHeader* header = (TexHeader*)data;
    uint32_t width = read_le32((uint8_t*)&header->width);
    uint32_t height = read_le32((uint8_t*)&header->height);
    uint8_t bpp = data[0x24];

    char output_path[1024];
    snprintf(output_path, sizeof(output_path), "%s/%s.png", 
             output_folder, strrchr(input_path, '/') ? strrchr(input_path, '/')+1 : input_path);

    int success = 0;
    uint8_t* rgb_data = NULL;
    
    if (bpp == 1) {
        rgb_data = convert_16bpp(data, width, height);
    } else if (bpp == 2) {
        rgb_data = convert_24bpp(data, width, height);
    } else {
        printf("未知色深: %d\n", bpp);
        free(data);
        return 0;
    }

    if (rgb_data) {
        success = stbi_write_png(output_path, width, height, 3, rgb_data, width * 3);
        free(rgb_data);
    }

    free(data);
    return success;
}

int main(int argc, char** argv) {
    if (argc < 3) {
        printf("用法: %s <输入目录> <输出目录>\n", argv[0]);
        return 1;
    }

    DIR* dir = opendir(argv[1]);
    if (!dir) {
        perror("无法打开目录");
        return 1;
    }

#ifdef _WIN32
    mkdir(argv[2]);
#else
    mkdir(argv[2], 0755);
#endif

    struct dirent* entry;
    int total = 0, success = 0;
    while ((entry = readdir(dir))) {
        if (strstr(entry->d_name, ".tex")) {
            char input_path[1024];
            snprintf(input_path, sizeof(input_path), "%s/%s", argv[1], entry->d_name);
            
            if (process_tex(input_path, argv[2])) {
                success++;
            }
            total++;
            printf("\r%d.%s", total,entry->d_name);
            fflush(stdout);
        }
    }

    closedir(dir);
    printf("\r转换完毕: 共%d个文件，成功%d个\n", total, success);
    return 0;
}