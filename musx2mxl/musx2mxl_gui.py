import os
import tkinter as tk
import traceback
from tkinter import filedialog, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from musx2mxl import convert_file
import threading

def main():

    def trim_path(path:str):
        max_length = 55  # Adjust based on actual display capacity
        if len(path) > max_length:
            path = "..." + path[-(max_length - 3):]  # Left trim with ellipsis
        return path

    def process_file(file_path):
        output_dir = os.path.dirname(file_path)
        output_path = os.path.join(output_dir, os.path.basename(file_path).replace(".musx", ".mxl"))
        try:
            convert_file(file_path, output_path)
            update_status(f"✔ Converted: {trim_path(output_path)}", "green")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            traceback.print_exc()
            update_status(f"❌ Error: {e}", "red")
        finally:
            convert_btn["state"] = "normal"
            loading_label.pack_forget()

    def start_conversion():
        file_path = entry_var.get()
        if file_path:
            convert_btn["state"] = "disabled"
            loading_label.pack(pady=5)
            threading.Thread(target=process_file, args=(file_path,), daemon=True).start()

    def browse_file():
        file_path = filedialog.askopenfilename(filetypes=[("Musx Files", "*.musx")])
        validate_file(file_path)

    def on_drop(event):
        file_path = event.data.strip('{}')  # Handle macOS extra braces
        validate_file(file_path)

    def validate_file(file_path):
        if file_path.lower().endswith(".musx"):
            entry_var.set(file_path)
            entry_trimmed_var.set(trim_path(file_path))
            convert_btn["state"] = "normal"
            update_status("✅ File selected!", "blue")
            drop_zone.config(bg="#dff0d8", fg="black")
        else:
            entry_var.set("")
            entry_trimmed_var.set("")
            convert_btn["state"] = "disabled"
            update_status("⚠ Invalid file. Please select a .musx file", "orange")
            drop_zone.config(bg="#eda6a6", fg="black")

    def update_status(message, color):
        status_label.config(text=message, foreground=color)

    root = TkinterDnD.Tk()
    root.title("Finale MUSX to MXL Converter")
    root.geometry("500x250")
    root.resizable(False, False)

    style = ttk.Style()
    style.configure("TButton", font=("Arial", 11))
    style.configure("TLabel", font=("Arial", 10))

    ttk.Label(root, text="Drag & Drop or Select a .musx File:", font=("Arial", 12, "bold")).pack(pady=10)

    entry_var = tk.StringVar()
    entry_trimmed_var = tk.StringVar()
    entry = ttk.Entry(root, textvariable=entry_trimmed_var, width=55, state="readonly", justify="center", font=("Arial", 10))
    entry.pack(pady=5, padx=10)

    drop_zone = tk.Label(root, text="⬇ Drag & Drop file here ⬇", bg="#f0f0f0", fg="gray", width=50, height=3, relief="ridge", borderwidth=2)
    drop_zone.pack(pady=5)
    drop_zone.drop_target_register(DND_FILES)
    drop_zone.dnd_bind('<<Drop>>', on_drop)

    button_frame = ttk.Frame(root)
    button_frame.pack(pady=10)

    browse_btn = ttk.Button(button_frame, text="Browse", command=browse_file, width=10)
    browse_btn.pack(side=tk.LEFT, padx=5)

    convert_btn = ttk.Button(button_frame, text="Convert", command=start_conversion, width=10, state="disabled")
    convert_btn.pack(side=tk.LEFT, padx=5)

    loading_label = ttk.Label(root, text="Converting...", foreground="orange")

    status_label = ttk.Label(root, text="", foreground="blue", anchor="center")
    status_label.pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()
