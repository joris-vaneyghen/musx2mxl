import os
import tkinter as tk
import traceback
from tkinter import filedialog

from tkinterdnd2 import DND_FILES, TkinterDnD

from musx2mxl import convert_file

def main():

    def process_file(file_path):
        if file_path.endswith(".musx"):
            output_dir = os.path.dirname(file_path)
            output_path = os.path.join(output_dir, os.path.basename(file_path).replace(".musx", ".mxl"))
            try:
                convert_file(file_path, output_path)
                status_label.config(text=f"Converted file saved to {output_path}", fg="green")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                traceback.print_exc()
                status_label.config(text=f"Error: {e}", fg="red")
        else:
            status_label.config(text="Invalid file type. Please select a .musx file", fg="red")

    def browse_file():
        file_path = filedialog.askopenfilename(filetypes=[("Musx Files", "*.musx")])
        if file_path:
            entry_var.set(file_path)

    def on_drop(event):
        file_path = event.data.strip('{}')  # Handle macOS extra braces
        entry_var.set(file_path)

    def convert():
        file_path = entry_var.get()
        if file_path:
            process_file(file_path)
        else:
            status_label.config(text="Please select a file first", fg="red")


    # GUI Setup
    root = TkinterDnD.Tk()
    root.title("Finale MUSX to MXL Converter")
    root.geometry("500x200")

    tk.Label(root, text="Select or Drag & Drop a .musx file:").pack(pady=5)
    entry_var = tk.StringVar()
    entry = tk.Entry(root, textvariable=entry_var, width=50)
    entry.pack(pady=5)

    frame = tk.Frame(root)
    frame.pack()

    browse_btn = tk.Button(frame, text="Browse", command=browse_file)
    browse_btn.pack(side=tk.LEFT, padx=5)

    convert_btn = tk.Button(frame, text="Convert", command=convert)
    convert_btn.pack(side=tk.LEFT, padx=5)

    status_label = tk.Label(root, text="", fg="blue")
    status_label.pack(pady=10)

    root.drop_target_register(DND_FILES)
    root.dnd_bind('<<Drop>>', on_drop)

    root.mainloop()


if __name__ == "__main__":
    main()