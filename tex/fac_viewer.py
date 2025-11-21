import pygame
import struct
import sys
import os
import random
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import math

# --- 全局配置 ---
BG_COLOR = (50, 50, 50)
SIDEBAR_BG = (35, 35, 35)
SIDEBAR_WIDTH = 250
BTN_COLOR = (70, 70, 70)
BTN_ACTIVE = (0, 100, 0)
TEXT_COLOR = (220, 220, 220)
HIGHLIGHT = (0, 120, 200)
INPUT_BG = (20, 20, 20)

# FAC 特征码
MAGIC_PATTERN = bytes.fromhex('00000000010000000000000010001000')

# --- 图像解析核心 ---
class ImageParser:
    @staticmethod
    def read_wh(data, offset=0):
        if len(data) < offset + 0x1C: return 0, 0
        w = struct.unpack('<H', data[offset + 0x18 : offset + 0x1a])[0]
        h = struct.unpack('<H', data[offset + 0x1a : offset + 0x1C])[0]
        return w, h

    @staticmethod
    def get_palette(palette_data):
        original = []
        for i in range(256):
            p = i * 4
            r, g, b, a = palette_data[p], palette_data[p+1], palette_data[p+2], palette_data[p+3]
            a = min(a * 2 - 1, 255)
            original.append((r, g, b, a))
        
        palette = []
        for major in range(0, 256, 32):
            group = original[major:major+32]
            reordered = group[0:8] + group[16:24] + group[8:16] + group[24:32]
            palette.extend(reordered)
        return palette

    @staticmethod
    def parse_4bpp(data):
        w, h = ImageParser.read_wh(data)
        if w == 0: return None
        pal_offset = struct.unpack('<I', data[0x1C:0x20])[0]
        palette = []
        for i in range(16):
            off = pal_offset + i*4
            r, g, b, a = data[off:off+4]
            a = min(a * 2 - 1, 255)
            palette.append((r, g, b, a))
        pixel_data = data[48:]
        img = Image.new('RGBA', (w, h))
        pixels = img.load()
        for y in range(h):
            for x in range(w):
                pos = y * w + x
                byte_pos = pos // 2
                if byte_pos >= len(pixel_data): break
                byte = pixel_data[byte_pos]
                idx = (byte >> (4 * (pos % 2))) & 0x0F
                pixels[x, y] = palette[idx]
        return img

    @staticmethod
    def parse_8bpp(data):
        w, h = ImageParser.read_wh(data)
        if w == 0: return None
        pal_off = data[0x1C] | (data[0x1D] << 8) | (data[0x1E] << 16)
        pal_data = data[pal_off : pal_off + 1024]
        palette = ImageParser.get_palette(pal_data)
        pixel_data = data[0x30:]
        img = Image.new('RGBA', (w, h))
        pixels = img.load()
        for y in range(h):
            for x in range(w):
                pixels[x, y] = palette[pixel_data[y * w + x]]
        return img

    @staticmethod
    def parse_16bpp(data):
        w, h = ImageParser.read_wh(data)
        if w == 0: return None
        pixel_data = data[0x20:]
        img = Image.new('RGB', (w, h))
        pixels = img.load()
        for y in range(h):
            for x in range(w):
                pos = (y * w + x) * 2
                if pos + 2 > len(pixel_data): break
                val = struct.unpack('<H', pixel_data[pos:pos+2])[0]
                b, g, r = (val >> 10) & 0x1F, (val >> 5) & 0x1F, val & 0x1F
                pixels[x, y] = (r << 3 | r >> 2, g << 3 | g >> 2, b << 3 | b >> 2)
        return img

    @staticmethod
    def parse_24bpp(data):
        w, h = ImageParser.read_wh(data)
        if w == 0: return None
        pixel_data = data[0x50:]
        img = Image.new('RGB', (w, h))
        pixels = img.load()
        for y in range(h):
            for x in range(w):
                pos = (y * w + x) * 3
                if pos + 3 > len(pixel_data): break
                pixels[x, y] = (pixel_data[pos], pixel_data[pos+1], pixel_data[pos+2])
        return img

    @staticmethod
    def parse_fac_layer(data, pattern_pos):
        # === 用户修正的偏移逻辑 ===
        pixel_start = pattern_pos + 16
        header_start = pattern_pos - 0x40
        
        if header_start < 0: return None
        
        try:
            # 读取宽高 (+0x38, +0x3A)
            w = struct.unpack('<H', data[header_start+0x38:header_start+0x3A])[0]
            h = struct.unpack('<H', data[header_start+0x3A:header_start+0x3C])[0]
            
            # 读取坐标 (+0x0C, +0x10) int
            x = struct.unpack('<i', data[header_start+0x0C:header_start+0x10])[0]
            y = struct.unpack('<i', data[header_start+0x10:header_start+0x14])[0]

            pixel_size = w * h
            pal_start = pixel_start + pixel_size
            
            # 防止越界
            if pal_start + 1024 > len(data): return None

            pal_data = data[pal_start : pal_start + 1024]
            palette = ImageParser.get_palette(pal_data)
            pixel_data = data[pixel_start : pal_start]
            
            img = Image.new('RGBA', (w, h))
            pixels = img.load()
            for py in range(h):
                for px in range(w):
                    idx = pixel_data[py * w + px]
                    pixels[px, py] = palette[idx]
            
            return img, x, y, w, h, (pal_start + 1024)
        except Exception as e:
            # print(f"Parse Error: {e}") 
            return None

# --- 主程序 ---
class FacPlayer:
    def __init__(self):
        pygame.init()
        try:
            self.font = pygame.font.SysFont("simhei", 16)
            self.list_font = pygame.font.SysFont("microsoftyahei", 13)
        except:
            self.font = pygame.font.SysFont("arial", 16)
            self.list_font = pygame.font.SysFont("arial", 13)

        self.window_w, self.window_h = 1100, 750
        self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)
        pygame.display.set_caption("Galaxy Angel II Viewer")
        self.clock = pygame.time.Clock()

        # 数据
        self.layers = {'body': None, 'eyes': [], 'mouths': []}
        self.filename = ""
        self.file_dir = ""
        self.full_file_list = []
        self.display_list = []
        self.list_scroll = 0
        self.selected_idx = -1
        self.is_agi = False

        # UI 状态
        self.filter_text = ""
        self.search_box_active = False
        self.is_dragging_scroll = False

        # 动画
        self.is_blinking = False
        self.is_talking = False
        self.blink_timer = -3.0
        self.blink_idx = 0
        self.blink_anim = False
        self.talk_timer = 0
        self.mouth_idx = 0
        self.blink_spd = 0.05
        self.talk_spd = 0.12

    def open_file_dialog(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="打开文件", filetypes=[("Texture", "*.fac;*.agi"), ("All", "*.*")]
        )
        root.destroy()
        if file_path:
            self.load_file(file_path)

    def get_current_composite_surface(self):
        """在原始尺寸下合成当前画面"""
        if not self.layers['body']: return None
        
        body = self.layers['body']
        # 创建原始尺寸画布
        canvas = pygame.Surface((body['w'], body['h']), pygame.SRCALPHA)
        
        # 绘制身体
        base_x, base_y = body['x'], body['y']
        canvas.blit(body['surf'], (0, 0))
        
        # 绘制眼睛
        if self.layers['eyes'] and self.blink_idx > 0 and self.blink_idx <= len(self.layers['eyes']):
            l = self.layers['eyes'][self.blink_idx-1]
            rel_x = l['x'] - base_x
            rel_y = l['y'] - base_y
            canvas.blit(l['surf'], (rel_x, rel_y))
            
        # 绘制嘴巴 - 修复索引检查
        if self.layers['mouths'] and self.mouth_idx > 0 and self.mouth_idx <= len(self.layers['mouths']):
            l = self.layers['mouths'][self.mouth_idx-1]
            rel_x = l['x'] - base_x
            rel_y = l['y'] - base_y
            canvas.blit(l['surf'], (rel_x, rel_y))
            
        return canvas

    def save_current_frame(self):
        canvas = self.get_current_composite_surface()
        if not canvas: return

        root = tk.Tk()
        root.withdraw()
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=f"{self.filename}_export.png",
            filetypes=[("PNG Image", "*.png")]
        )
        root.destroy()
        
        if save_path:
            try:
                pygame.image.save(canvas, save_path)
                print(f"已保存: {save_path}")
            except Exception as e:
                print(f"保存失败: {e}")

    def scan_dir(self, path):
        self.file_dir = os.path.dirname(path)
        try:
            files = [f for f in os.listdir(self.file_dir) if f.lower().endswith(('.fac', '.agi'))]
            files.sort()
            self.full_file_list = files
            self.update_filter()
        except:
            self.full_file_list = []
            self.display_list = []

    def update_filter(self):
        if not self.filter_text:
            self.display_list = self.full_file_list[:]
        else:
            self.display_list = [f for f in self.full_file_list if self.filter_text.lower() in f.lower()]
        
        # 自动定位
        if self.filename in self.display_list:
            idx = self.display_list.index(self.filename)
            self.selected_idx = idx
            # 计算居中位置
            visible_count = (self.window_h - 60) // 25
            target_scroll = idx - (visible_count // 2)
            self.list_scroll = max(0, target_scroll)
        else:
            self.selected_idx = -1

    def load_file(self, path):
        self.filename = os.path.basename(path)
        if os.path.dirname(path) != self.file_dir:
            self.scan_dir(path)
        else:
            self.update_filter()

        self.layers = {'body': None, 'eyes': [], 'mouths': []}
        self.is_agi = False
        print(f"加载: {self.filename}")
        
        try:
            with open(path, 'rb') as f:
                data = f.read()

            # 1. AGI Check
            if len(data) > 0x30:
                flag = data[0x2c:0x30].hex()
                pil_img = None
                if flag == '44494449': pil_img = ImageParser.parse_16bpp(data)
                elif flag == "00300100": pil_img = ImageParser.parse_24bpp(data)
                elif flag == '10001000': pil_img = ImageParser.parse_8bpp(data)
                elif flag in ['00001400', "08000200"]: pil_img = ImageParser.parse_4bpp(data)
                
                if pil_img:
                    self.is_agi = True
                    mode = pil_img.mode
                    surf = pygame.image.fromstring(pil_img.tobytes(), pil_img.size, mode)
                    self.layers['body'] = {'surf': surf, 'x': 0, 'y': 0, 'w': pil_img.width, 'h': pil_img.height}
                    return

            # 2. FAC Violence Search
            search_pos = 0
            found_count = 0
            while True:
                idx = data.find(MAGIC_PATTERN, search_pos)
                if idx == -1: break
                res = ImageParser.parse_fac_layer(data, idx)
                if res:
                    pil_img, x, y, w, h, next_pos = res
                    surf = pygame.image.fromstring(pil_img.tobytes(), pil_img.size, pil_img.mode)
                    layer = {'surf': surf, 'x': x, 'y': y, 'w': w, 'h': h}
                    
                    if found_count == 0:
                        self.layers['body'] = layer
                    elif found_count <= 2: # 假设接下来的2个是眼睛
                        self.layers['eyes'].append(layer)
                    else:
                        self.layers['mouths'].append(layer)
                    found_count += 1
                    search_pos = next_pos
                else:
                    search_pos = idx + 16

            self.blink_timer = -3.0
            self.blink_idx = 0

        except Exception as e:
            print(f"Error: {e}")

    def update(self, dt):
        if self.is_agi: return
        # 眨眼
        if self.is_blinking and self.layers['eyes']:
            if not self.blink_anim:
                self.blink_timer += dt
                self.blink_idx = 0
                if self.blink_timer >= 0:
                    self.blink_anim = True
                    self.blink_frame_timer = 0
            else:
                self.blink_frame_timer += dt
                total = len(self.layers['eyes']) + 1
                seq = list(range(total)) + list(range(total-2, -1, -1))
                seq = [x for x in seq if x >= 0]
                step = int(self.blink_frame_timer / self.blink_spd)
                if step < len(seq): self.blink_idx = seq[step]
                else:
                    self.blink_anim = False
                    self.blink_timer = -3.0 - random.random()
        elif self.layers['eyes']:
            self.blink_idx = 0
        # 说话
        if self.is_talking and self.layers['mouths']:
            self.talk_timer += dt
            if self.talk_timer > self.talk_spd:
                self.talk_timer = 0
                self.mouth_idx = random.randint(0, len(self.layers['mouths']))
        else: self.mouth_idx = 0

    def draw_sidebar(self, w, h):
        sx = w - SIDEBAR_WIDTH
        pygame.draw.rect(self.screen, SIDEBAR_BG, (sx, 0, SIDEBAR_WIDTH, h))
        pygame.draw.line(self.screen, (80,80,80), (sx, 0), (sx, h), 1)

        # --- 搜索框 ---
        search_rect = pygame.Rect(sx + 10, 10, SIDEBAR_WIDTH - 20, 30)
        col = (50,50,50) if not self.search_box_active else (70,70,70)
        pygame.draw.rect(self.screen, col, search_rect, border_radius=4)
        pygame.draw.rect(self.screen, (100,100,100), search_rect, 1, border_radius=4)
        
        # 文字 + 光标
        disp_txt = self.filter_text
        txt_col = (255,255,255)
        if not disp_txt and not self.search_box_active:
            disp_txt = "搜索..."
            txt_col = (150,150,150)
        
        t_surf = self.font.render(disp_txt, True, txt_col)
        self.screen.blit(t_surf, (sx + 15, 16))
        
        # 绘制光标 (闪烁)
        if self.search_box_active and (pygame.time.get_ticks() // 500) % 2 == 0:
            cursor_x = sx + 15 + t_surf.get_width()
            pygame.draw.line(self.screen, (255,255,255), (cursor_x, 15), (cursor_x, 35), 1)

        # --- 列表 ---
        list_top = 50
        item_h = 25
        max_vis = (h - list_top) // item_h
        
        if not self.display_list: return

        self.list_scroll = max(0, min(self.list_scroll, len(self.display_list) - max_vis))
        if len(self.display_list) <= max_vis: self.list_scroll = 0

        start = int(self.list_scroll)
        end = min(start + max_vis + 1, len(self.display_list))
        
        mouse_pos = pygame.mouse.get_pos()

        for i in range(start, end):
            fname = self.display_list[i]
            rect = pygame.Rect(sx, list_top + (i-start)*item_h, SIDEBAR_WIDTH - 12, item_h)
            
            if i == self.selected_idx:
                pygame.draw.rect(self.screen, HIGHLIGHT, rect)
            
            if rect.collidepoint(mouse_pos) and mouse_pos[0] > sx:
                if i != self.selected_idx:
                    pygame.draw.rect(self.screen, (60,60,60), rect)
            
            disp = fname if len(fname) < 28 else fname[:25]+"..."
            txt = self.list_font.render(disp, True, TEXT_COLOR)
            self.screen.blit(txt, (sx + 5, rect.y + 4))

        # --- 滚动条 ---
        if len(self.display_list) > max_vis:
            track_h = h - list_top
            bar_h = max(30, track_h * (max_vis / len(self.display_list)))
            bar_y = list_top + (self.list_scroll / len(self.display_list)) * track_h
            
            bar_rect = pygame.Rect(w - 10, bar_y, 8, bar_h)
            col = (150,150,150) if self.is_dragging_scroll or bar_rect.collidepoint(mouse_pos) else (100,100,100)
            pygame.draw.rect(self.screen, col, bar_rect, border_radius=4)

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN and self.search_box_active:
            if event.key == pygame.K_BACKSPACE:
                self.filter_text = self.filter_text[:-1]
            else:
                if len(event.unicode) > 0 and event.unicode.isprintable():
                    self.filter_text += event.unicode
            self.update_filter()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            events = pygame.event.get()
            w, h = self.screen.get_size()
            sx = w - SIDEBAR_WIDTH

            for e in events:
                if e.type == pygame.QUIT: running = False
                elif e.type == pygame.VIDEORESIZE:
                    self.window_w, self.window_h = e.w, e.h
                    self.screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)

                self.handle_input(e)

                if e.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = e.pos
                    if e.button == 1:
                        # 搜索框
                        search_rect = pygame.Rect(sx + 10, 10, SIDEBAR_WIDTH - 20, 30)
                        if search_rect.collidepoint(e.pos):
                            self.search_box_active = True
                        else:
                            self.search_box_active = False
                        
                        # 滚动条
                        if mx > w - 15 and my > 50:
                            self.is_dragging_scroll = True

                        # 列表
                        if sx < mx < w - 15 and my > 50:
                            item_h = 25
                            idx = int(self.list_scroll + (my - 50) // item_h)
                            if 0 <= idx < len(self.display_list):
                                path = os.path.join(self.file_dir, self.display_list[idx])
                                self.load_file(path)

                elif e.type == pygame.MOUSEBUTTONUP:
                    self.is_dragging_scroll = False

                elif e.type == pygame.MOUSEMOTION:
                    if self.is_dragging_scroll and len(self.display_list) > 0:
                        track_h = h - 50
                        ratio = (e.pos[1] - 50) / track_h
                        self.list_scroll = int(ratio * len(self.display_list))

                elif e.type == pygame.MOUSEWHEEL:
                    if pygame.mouse.get_pos()[0] > sx:
                        self.list_scroll -= e.y * 3

            self.update(dt)
            self.screen.fill(BG_COLOR)
            
            # --- 核心绘图 (自动缩放与合成) ---
            view_w = w - SIDEBAR_WIDTH
            view_h = h - 60 # 减去底部高度

            composite = self.get_current_composite_surface()
            
            if composite:
                img_w = composite.get_width()
                img_h = composite.get_height()
                
                # 计算缩放比例 (保持比例)
                scale = 1.0
                if img_w > view_w or img_h > view_h:
                    scale = min(view_w / img_w, view_h / img_h) * 0.95 # 留点边距
                
                # 缩放
                if scale != 1.0:
                    new_size = (int(img_w * scale), int(img_h * scale))
                    final_surf = pygame.transform.smoothscale(composite, new_size)
                else:
                    final_surf = composite

                # 居中显示
                dest_x = (view_w - final_surf.get_width()) // 2
                dest_y = (view_h - final_surf.get_height()) // 2
                
                self.screen.blit(final_surf, (dest_x, dest_y))
            else:
                t = self.font.render("请加载文件", True, (150,150,150))
                self.screen.blit(t, (view_w//2-40, h//2))

            # 底部按钮
            if not self.is_agi:
                py = h - 60
                pygame.draw.rect(self.screen, (40,40,40), (0, py, view_w, 60))
                
                def btn(rect, txt, active, cb):
                    col = BTN_ACTIVE if active else BTN_COLOR
                    if rect.collidepoint(pygame.mouse.get_pos()): col = (col[0]+30,col[1]+30,col[2]+30)
                    pygame.draw.rect(self.screen, col, rect, border_radius=4)
                    ts = self.font.render(txt, True, TEXT_COLOR)
                    self.screen.blit(ts, ts.get_rect(center=rect.center))
                    for ev in events:
                        if ev.type == pygame.MOUSEBUTTONDOWN and rect.collidepoint(ev.pos): cb()
                
                btn(pygame.Rect(10, py+10, 80, 40), "加载", False, self.open_file_dialog)
                btn(pygame.Rect(100, py+10, 80, 40), "眨眼", self.is_blinking, lambda: setattr(self, 'is_blinking', not self.is_blinking))
                btn(pygame.Rect(190, py+10, 80, 40), "说话", self.is_talking, lambda: setattr(self, 'is_talking', not self.is_talking))
                btn(pygame.Rect(280, py+10, 80, 40), "保存", False, self.save_current_frame)
            else:
                py = h - 60
                pygame.draw.rect(self.screen, (40,40,40), (0, py, view_w, 60))
                def btn(rect, txt, cb):
                    col = BTN_COLOR
                    if rect.collidepoint(pygame.mouse.get_pos()): col = (100,100,100)
                    pygame.draw.rect(self.screen, col, rect, border_radius=4)
                    ts = self.font.render(txt, True, TEXT_COLOR)
                    self.screen.blit(ts, ts.get_rect(center=rect.center))
                    for ev in events:
                        if ev.type == pygame.MOUSEBUTTONDOWN and rect.collidepoint(ev.pos): cb()
                btn(pygame.Rect(10, py+10, 80, 40), "加载", self.open_file_dialog)
                self.screen.blit(self.font.render("AGI 模式", True, (100,100,100)), (100, py+20))

            self.draw_sidebar(w, h)
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    FacPlayer().run()