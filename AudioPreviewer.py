# AudioPreviewer.py
import tkinter as tk
from tkinter import ttk
import threading
import tempfile
from pydub import AudioSegment
from pydub.playback import play
import os
import sounddevice as sd
from io import BytesIO
import numpy as np



class AudioPreviewer:
    def __init__(self, parent, process_callback):
        self.parent = parent
        self.process_audio = process_callback
        self.preview_playing = False
        
        self.preview_frame = ttk.Frame(self.parent)
        self.btn_preview = ttk.Button(
            self.preview_frame,
            text="▶️ Prévia",
            command=self.toggle_preview
        )
        self.btn_stop = ttk.Button(
            self.preview_frame,
            text="⏹️ Parar",
            command=self.stop_preview,
            state=tk.DISABLED
        )
        self.btn_preview.pack(side=tk.LEFT, padx=5)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

    def get_widget(self):
        return self.preview_frame

    def toggle_preview(self):
        if not self.preview_playing:
            self.start_preview()
        else:
            self.stop_preview()

    def start_preview(self):
        self.preview_playing = True
        self.btn_preview.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        threading.Thread(target=self._preview_thread).start()

    def stop_preview(self):
        self.preview_playing = False
        self.btn_preview.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def _preview_thread(self):
        try:
            processed_audio = self.process_audio()
            if processed_audio:
                # Conversão direta para numpy array com dtype correto
                samples = np.array(
                    processed_audio.get_array_of_samples(),
                    dtype=np.int16  # Força o tipo para 16-bit
                )
                
                # Configurações de reprodução
                samplerate = processed_audio.frame_rate
                channels = processed_audio.channels
                
                # Reformata o array para 2D se for mono
                if channels == 1:
                    samples = samples.reshape(-1, 1)
                
                # Reprodução direta com sounddevice
                self.stream = sd.OutputStream(
                    samplerate=samplerate,
                    channels=channels,
                    dtype=np.int16,
                    blocksize=1024,
                    latency='low'
                )
                
                self.stream.start()
                self.stream.write(samples)
                
                # Mantém a reprodução ativa
                while self.preview_playing and self.stream.active:
                    sd.sleep(100)

        except Exception as e:
            print(f"Erro na prévia: {str(e)}")
        finally:
            self.stop_preview()