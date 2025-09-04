import tkinter as tk
from tkinter import ttk
from bitConverter import CleanRetroConverter
import tkinter as tk
from tkinter import ttk
from bitConverter import CleanRetroConverter

class SimpleConverterUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Conversor 8-Bit")
        self.root.geometry("300x200")
        
        self.converter = CleanRetroConverter()
        
        self.main_frame = ttk.Frame(root, padding=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.create_widgets()
        self.converter.status = self.status_label

    def create_widgets(self):
        # Botão de carregar
        ttk.Button(
            self.main_frame,
            text="Carregar Áudio",
            command=self.converter.load_audio,
            width=20
        ).pack(pady=10)
        
        # Botão de prévia
        ttk.Button(
            self.main_frame,
            text="Ouvir Prévia",
            command=self.converter.preview,
            width=20
        ).pack(pady=5)
        
        # Botão de converter
        ttk.Button(
            self.main_frame,
            text="Converter para 8-bit",
            command=self.converter.save,
            width=20
        ).pack(pady=10)
        
        # Status - alterado para tk.Label
        self.status_label = tk.Label(  # Use tk.Label em vez de ttk.Label
            self.main_frame, 
            text="Pronto.",
            fg="black"  # Cor padrão
        )
        self.status_label.pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleConverterUI(root)
    root.mainloop()