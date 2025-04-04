#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define WINDOW_SIZE 4096
#define MAX_MATCH_LEN 18
#define MIN_MATCH_LEN 3
#define CONTROL_XOR 0x72
#define LOG_SUFFIX ".clog"
#define HEADER_MAGIC "\x20\x33\x3B\x31"

typedef struct {
    uint8_t data[WINDOW_SIZE];
    int pos;
    int size;
} SlidingWindow;

typedef struct {
    FILE* fp;
    int ctrl_groups;
    int lz77_blocks;
    int raw_bytes;
} CompressLogger;

void log_init(CompressLogger* logger, const char* output_path) {
    char log_path[256];
    snprintf(log_path, sizeof(log_path), "%s%s", output_path, LOG_SUFFIX);
    logger->fp = fopen(log_path, "w");
    fprintf(logger->fp, "=== Compression Log ===\n");
    logger->ctrl_groups = logger->lz77_blocks = logger->raw_bytes = 0;
}

void log_control_group(CompressLogger* logger, int file_offset, uint8_t mask) {
    fprintf(logger->fp, "[CTRL] Group %d @0x%04X (0x%02X)\n", 
           ++logger->ctrl_groups, file_offset, mask);
}

void log_lz77_block(CompressLogger* logger, int file_offset, int dist, int len) {
    fprintf(logger->fp, "[LZ77] @0x%04X: d=0x%03X l=%d\n", 
           file_offset, dist, len);
    logger->lz77_blocks++;
}

void log_raw_byte(CompressLogger* logger, int file_offset, uint8_t value) {
    if (logger->raw_bytes++ % 8 == 0) {
        fprintf(logger->fp, "[RAW]  @0x%04X: 0x%02X\n", file_offset, value);
    }
}

void log_close(CompressLogger* logger) {
    fprintf(logger->fp, "\n=== Summary ===\n");
    fprintf(logger->fp, "Control groups: %d\n", logger->ctrl_groups);
    fprintf(logger->fp, "LZ77 blocks:    %d\n", logger->lz77_blocks);
    fprintf(logger->fp, "Raw bytes:      %d\n", logger->raw_bytes);
    fclose(logger->fp);
}

void window_init(SlidingWindow* window) {
    memset(window->data, 0, WINDOW_SIZE);
    window->pos = 0xFEE;
    window->size = 0;
}

void window_update(SlidingWindow* window, uint8_t byte) {
    window->data[window->pos] = byte;
    window->pos = (window->pos + 1) % WINDOW_SIZE;
    if (window->size < WINDOW_SIZE) window->size++;
}

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

void compress(FILE* in, FILE* out, const char* out_name) {
    CompressLogger logger;
    log_init(&logger, out_name);
    
    fseek(in, 0, SEEK_END);
    long file_size = ftell(in);
    fseek(in, 0, SEEK_SET);
    uint8_t* input = malloc(file_size);
    fread(input, 1, file_size, in);
    
    fwrite(HEADER_MAGIC, 1, 4, out);
    fwrite(&file_size, 4, 1, out);
    
    SlidingWindow window;
    window_init(&window);
    
    int read_pos = 0;
    int output_pos = 8;
    uint8_t control_mask = 0;
    int control_bit = 0;
    uint8_t data_buffer[16];
    int data_buffer_len = 0;
    
    while (read_pos < file_size) {
        int distance, match_len = 0;
        if (window.size >= MIN_MATCH_LEN) {
            match_len = find_match(&window, input, read_pos, file_size, &distance);
        }
        
        if (match_len >= MIN_MATCH_LEN) {
            control_mask |= (0 << control_bit);
            
            uint8_t byte1 = distance & 0xFF;
            uint8_t byte2 = ((distance >> 4) & 0xF0) | ((match_len - 3) & 0x0F);
            
            data_buffer[data_buffer_len++] = byte1 ^ CONTROL_XOR;
            data_buffer[data_buffer_len++] = byte2 ^ CONTROL_XOR;
            log_lz77_block(&logger, output_pos + data_buffer_len - 2, distance, match_len);
            
            for (int i = 0; i < match_len; i++) {
                window_update(&window, input[read_pos + i]);
            }
            read_pos += match_len;
        } else {
            control_mask |= (1 << control_bit);
            
            uint8_t value = input[read_pos];
            data_buffer[data_buffer_len++] = value ^ CONTROL_XOR;
            log_raw_byte(&logger, output_pos + data_buffer_len - 1, value);
            
            window_update(&window, value);
            read_pos++;
        }
        control_bit++;
        
        if (control_bit >= 8) {
            uint8_t ctrl_byte = control_mask ^ CONTROL_XOR;
            fputc(ctrl_byte, out);
            log_control_group(&logger, output_pos, ctrl_byte);
            fwrite(data_buffer, 1, data_buffer_len, out);
            
            output_pos += 1 + data_buffer_len;
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
        uint8_t ctrl_byte = control_mask ^ CONTROL_XOR;
        fputc(ctrl_byte, out);
        log_control_group(&logger, output_pos, ctrl_byte);
        fwrite(data_buffer, 1, data_buffer_len, out);
        output_pos += 1 + data_buffer_len;
    }
    
    log_close(&logger);
    free(input);
}

int main(int argc, char** argv) {
    if (argc != 3) {
        printf("Usage: %s <input> <output>\n", argv[0]);
        return 1;
    }
    
    FILE* in = fopen(argv[1], "rb");
    if (!in) {
        perror("Input open failed");
        return 2;
    }
    
    FILE* out = fopen(argv[2], "wb");
    if (!out) {
        perror("Output create failed");
        fclose(in);
        return 3;
    }
    
    compress(in, out, argv[2]);
    
    fclose(in);
    fclose(out);
    printf("Compression completed. Log: %s%s\n", argv[2], LOG_SUFFIX);
    return 0;
}
