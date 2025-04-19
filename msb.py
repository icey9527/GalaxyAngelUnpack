import os
import sys
import threading
import subprocess

def decode_shift_jis(data, encoding='shift-jis'):
    null_index = data.find(b'\x00')
    if null_index != -1:
        data = data[:null_index]
    try:
        decoded_str = data.decode(encoding)
        return decoded_str
    except UnicodeDecodeError:
        print("解码 Shift-JIS 时出现错误")
        return None




def convert_mb_to_wav(input_file, output_file, sample_rate=23000):
    """线程安全的版本，限制同时运行的进程数"""
    # 获取信号量（如果已达最大并发数，会阻塞等待）
    semaphore.acquire()
    
    # 启动线程执行实际任务（将逻辑移到线程内）
    def _task():
        try:
            subprocess.run(
                f'..\\MFAudio.exe /IF{sample_rate} /IC1 /IH40 /OTWAVU /OF{sample_rate} /OC1 "{input_file}" "{output_file}"',
                shell=True,
                cwd=input,  # 注意：确保这里是有效的路径字符串！
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            print(f"转换失败: {input_file}, 错误: {e.stderr.decode('utf-8')}")
        finally:
            semaphore.release()  # 确保信号量一定会释放
    
    thread = threading.Thread(target=_task)
    thread.start()

def raw_to_wav(data, 编号):
    filename = decode_shift_jis(data[0x20:0x40])
    filename, suffix = os.path.splitext(filename)
    
    print(str(编号)+ '.' + filename+'.wav')
    采样率 = int.from_bytes(data[0x12:0x14], 'big')
    #print(hex(int.from_bytes(data[0x10:0x14], 'little')))
    with open(f"{input}/{filename+".mb"}", 'wb') as f:
        f.write(data)
    convert_mb_to_wav(filename+".mb",filename+".wav",采样率)
    
    



def main():
    with open(input+ ".msh", 'rb') as msh_file, open(input +'.msb', 'rb') as msb_file:
        msh_file.seek(0xc)

        for i in range(999999):
            size = int.from_bytes(msh_file.read(4), 'little')
            编号 = int.from_bytes(msh_file.read(4), 'little')
            地址 = int.from_bytes(msh_file.read(4), 'little')
            type = int.from_bytes(msh_file.read(4), 'little')
            if size == 0 or  type ==0:
                break
            msb_file.seek(地址)
            #print(size,编号,地址,type)
            data = msb_file.read(size)
            #with open(f'{input}/{编号}.mb', 'wb') as f:
            #    f.write(data)
            raw_to_wav(data, 编号)


# 全局信号量，限制最大并发数（例如设为10）
MAX_CONCURRENT_PROCESSES = 30 
semaphore = threading.Semaphore(MAX_CONCURRENT_PROCESSES)

semaphore.acquire()
    


if __name__ == "__main__":
    if len(sys.argv) == 2:
        input = sys.argv[1]
        os.makedirs(input, exist_ok=True)
        main()