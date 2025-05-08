import tkinter as tk
from tkinter import filedialog, ttk
from pydub import AudioSegment
import numpy as np
import os
from scipy import signal
from pydub import AudioSegment
from pydub.playback import play
from AudioPreviewer import AudioPreviewer
import threading;

class AdvancedBitCrusher:
    def __init__(self, root):
        self.root = root
        self.root.title("Decimort-like Converter")
        self.root.geometry("600x500")

        self.input_file = ""
        self.bit_depth = tk.IntVar(value=8)
        self.sample_rate = tk.IntVar(value=44100)
        self.dry_wet = tk.DoubleVar(value=1.0)
        self.resample_quality = tk.StringVar(value="High")

    
        self.main_frame = tk.Frame(self.root, padx=20, pady=20)
        self.main_frame.pack(expand=True, fill=tk.BOTH)

        self.previewer = AudioPreviewer(self.main_frame, self.preview_audio)
        self.create_widgets()



    def create_widgets(self):
        main_frame = self.main_frame
        main_frame.pack(expand=True, fill=tk.BOTH)

        # File Selection
        btn_select = tk.Button(
            main_frame,
            text="Carregar Áudio",
            command=self.load_audio,
            bg="#2E7D32",
            fg="white"
        )
        btn_select.pack(pady=10, fill=tk.X)

        # Resampler Controls
        resample_frame = tk.LabelFrame(main_frame, text="Controle de Resampling")
        resample_frame.pack(pady=10, fill=tk.X)

        # kHz Slider
        self.khz_slider = ttk.Scale(
            resample_frame,
            from_=1,
            to=48,
            variable=self.sample_rate,
            orient=tk.HORIZONTAL,
            length=300,
            command=lambda v: self.sample_rate.set(int(float(v)*1000))
        )
        self.khz_slider.pack(pady=5)
        self.khz_label = tk.Label(resample_frame, text="Taxa de Amostragem: 44.1 kHz")
        self.khz_label.pack()

        # Quality Settings
        quality_frame = tk.Frame(resample_frame)
        quality_frame.pack(pady=5)
        ttk.Label(quality_frame, text="Qualidade:").pack(side=tk.LEFT)
        ttk.Combobox(
            quality_frame,
            textvariable=self.resample_quality,
            values=["Low (Fast)", "Medium", "High (Slow)"],
            state="readonly",
            width=12
        ).pack(side=tk.LEFT, padx=10)

        # Bit Crusher Controls
        bit_frame = tk.LabelFrame(main_frame, text="Bit Crusher")
        bit_frame.pack(pady=10, fill=tk.X)

        ttk.Label(bit_frame, text="Bits:").pack(side=tk.LEFT)
        ttk.Scale(
            bit_frame,
            variable=self.bit_depth,
            from_=1,
            to=16,
            orient=tk.HORIZONTAL,
            length=200
        ).pack(side=tk.LEFT, padx=10)
        self.bit_label = tk.Label(bit_frame, text="8 bits")
        self.bit_label.pack(side=tk.LEFT)

        # Dry/Wet Mix
        mix_frame = tk.LabelFrame(main_frame, text="Mixagem")
        mix_frame.pack(pady=10, fill=tk.X)
        ttk.Scale(
            mix_frame,
            variable=self.dry_wet,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            length=200
        ).pack(pady=5)
        self.mix_label = tk.Label(mix_frame, text="100% Processado")
        self.mix_label.pack()

        # Process Button
        btn_process = tk.Button(
            main_frame,
            text="Salvar Áudio",
            command=self.save_audio,  # Alterado para save_audio
            bg="#1565C0",
            fg="white"
        )
        btn_process.pack(pady=15, fill=tk.X)

        # Status
        self.status = tk.Label(main_frame, text="", fg="#666")
        self.status.pack()

        # Bindings
        self.bit_depth.trace_add("write", self.update_bit_label)
        self.sample_rate.trace_add("write", self.update_khz_label)
        self.dry_wet.trace_add("write", self.update_mix_label)
        self.previewer.get_widget().pack(pady=10, fill=tk.X)
    
    def play_processed_audio(self):
            processed_audio = self.process_audio(show_dialog=False)
            if processed_audio:
                threading.Thread(target=lambda: play(processed_audio)).start()
        
    def preview_audio(self):
        """Processa o áudio apenas para prévia (sem diálogo de salvamento)"""
        return self.process_audio(show_dialog=False)

    def save_audio(self):
        """Processa e salva o áudio (com diálogo de salvamento)"""
        self.process_audio(show_dialog=True)


    def update_bit_label(self, *args):
        self.bit_label.config(text=f"{self.bit_depth.get()} bits")

    def update_khz_label(self, *args):
        khz = self.sample_rate.get() / 1000
        self.khz_label.config(text=f"Taxa de Amostragem: {khz:.1f} kHz")

    def update_mix_label(self, *args):
        mix = int(self.dry_wet.get() * 100)
        self.mix_label.config(text=f"Processado: {mix}% | Original: {100 - mix}%")

    def load_audio(self):
        self.input_file = filedialog.askopenfilename(
            filetypes=(("Arquivos de Áudio", "*.wav *.mp3 *.ogg"),)
        )
        if self.input_file:
            self.status.config(text=f"Arquivo carregado: {os.path.basename(self.input_file)}", fg="green")

    def resample_signal(self, data, original_rate, target_rate):
        quality = self.resample_quality.get()
        
        if original_rate == target_rate:
            return data

        ratio = target_rate / original_rate
        new_length = int(len(data) * ratio)

        if quality == "Low (Fast)":
            return signal.resample(data, new_length)
        elif quality == "Medium":
            return signal.resample_poly(data, target_rate, original_rate)
        else:  # High Quality
            return signal.resample(data, new_length, window=('kaiser', 5.0))
        
        
        
 

    def process_audio(self,show_dialog=False):
        if not self.input_file:
            self.status.config(text="Selecione um arquivo primeiro!", fg="red")
            return

        try:
            # Carregar áudio
            audio = AudioSegment.from_file(self.input_file)
            original = audio.set_channels(1)
            samples = np.array(original.get_array_of_samples(), dtype=np.float32) / 32768.0

            # Parâmetros
            target_rate = self.sample_rate.get()
            bits = self.bit_depth.get()
            mix = self.dry_wet.get()

            # Resampling
            resampled = self.resample_signal(samples, original.frame_rate, target_rate)

            # Bit crushing
            max_val = 2**(bits - 1) - 1
            crushed = np.floor(resampled * max_val) / max_val

            # Mixagem
            if mix < 1.0:
                original_resampled = signal.resample(samples, len(crushed))
                processed = (crushed * mix) + (original_resampled * (1 - mix))
            else:
                processed = crushed

            # Converter para bytes
            final = (processed * 32767).astype(np.int16).tobytes()

            # Criar áudio
            output = AudioSegment(
                final,
                frame_rate=target_rate,
                sample_width=2,
                channels=1
            )
            if show_dialog:
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".wav",
                    filetypes=(("Arquivo WAV", "*.wav"),),
                    initialfile=f"processed_{os.path.basename(self.input_file)}"
                )
                if save_path:
                    output.export(save_path, format="wav")
                    self.status.config(text=f"Arquivo salvo: {save_path}", fg="green")

            return output.set_sample_width(2)
          
            

        


        except Exception as e:
            self.status.config(text=f"Erro: {str(e)}", fg="red")
            return None

if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedBitCrusher(root)
    root.mainloop()
    