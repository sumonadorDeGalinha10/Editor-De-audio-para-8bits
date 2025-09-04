import tkinter as tk
from tkinter import filedialog
from pydub import AudioSegment
import numpy as np
import os
import threading
import sounddevice as sd
import logging
from scipy import signal

class CleanRetroConverter:
    def __init__(self):
        self.input_file = ""
        self.status = None
        logging.basicConfig(level=logging.INFO)
        
        self.bit_depth = 4
        self.internal_rate = 44100  
        self.output_rate = 11025    
        
     
        self.quantization_levels = 16  

    def load_audio(self):
        self.input_file = filedialog.askopenfilename(
            filetypes=(("Arquivos de Áudio", "*.wav *.mp3 *.ogg *.flac"),)
        )
        if self.input_file and self.status:
            self.status.config(text=f"Carregado: {os.path.basename(self.input_file)}")
            self.status.config(fg="green")

    def clean_bitcrush(self, samples, original_rate):
        """
        Aplica redução de bits e sample rate de forma limpa
        sem adicionar ruído ou distorção indesejada
        """
        # 1. Redimensiona para taxa interna de processamento
        if original_rate != self.internal_rate:
            samples = signal.resample(samples, int(len(samples) * self.internal_rate / original_rate))
        
  
        nyquist = 0.5 * self.internal_rate
        cutoff = min(4000, 0.45 * self.output_rate)  # Prevenir aliasing
        normal_cutoff = cutoff / nyquist
        b, a = signal.butter(4, normal_cutoff, btype='low')
        filtered = signal.filtfilt(b, a, samples)
        
   
        output_length = int(len(filtered) * self.output_rate / self.internal_rate)
        downsampled = signal.resample(filtered, output_length)
        
     
        scale = self.quantization_levels / 2
        quantized = np.round(downsampled * scale) / scale
        
        return quantized

    def convert_to_retro(self, show_dialog=False):
        if not self.input_file:
            if self.status:
                self.status.config(text="Selecione um arquivo primeiro!", fg="red")
            return None

        try:

            audio = AudioSegment.from_file(self.input_file)
            original = audio.set_channels(1).set_frame_rate(self.internal_rate)
            samples = np.array(original.get_array_of_samples(), dtype=np.float32)
            samples = samples / np.max(np.abs(samples))  # Normaliza
            
    
            processed = self.clean_bitcrush(samples, self.internal_rate)
            
       
            processed = np.clip(processed, -0.99, 0.99)
            
         
            int_samples = (processed * 127).astype(np.int8)
            output = AudioSegment(
                int_samples.tobytes(),
                frame_rate=self.output_rate,
                sample_width=1,
                channels=1
            )
  
            if show_dialog:
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".wav",
                    filetypes=(("Arquivo WAV", "*.wav"),),
                    initialfile=f"clean_retro_{os.path.basename(self.input_file)}"
                )
                if save_path:
                    output.export(save_path, format="wav")
                    if self.status:
                        self.status.config(text=f"Áudio retro limpo salvo!", fg="green")
            
            return output

        except Exception as e:
            if self.status:
                self.status.config(text=f"Erro: {str(e)}", fg="red")
            logging.error(f"Erro no processamento: {str(e)}", exc_info=True)
            return None

    def preview(self):
        output = self.convert_to_retro()
        if output:
            threading.Thread(target=self.play_audio_directly, args=(output,), daemon=True).start()
    
    def play_audio_directly(self, audio):
        """Reprodução direta sem chiado"""
        try:
            samples = np.array(audio.get_array_of_samples())
            samplerate = audio.frame_rate
            
     
            sd.default.samplerate = samplerate
            sd.default.dtype = 'int8'
            sd.default.channels = 1
            
            sd.play(samples)
            sd.wait()
        except Exception as e:
            if self.status:
                self.status.config(text=f"Erro na prévia: {str(e)}", fg="red")
            logging.error(f"Erro na reprodução: {str(e)}")
    
    def save(self):
        self.convert_to_retro(show_dialog=True)