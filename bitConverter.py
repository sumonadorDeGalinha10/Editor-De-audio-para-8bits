import tkinter as tk
from tkinter import filedialog
from pydub import AudioSegment
import numpy as np
import os
import threading
import sounddevice as sd
import logging
from scipy import signal

logging.basicConfig(level=logging.INFO)

class CleanRetroConverter:
    def __init__(self):
        self.input_file = ""
        self.status = None

        # Parâmetros principais
        self.internal_rate = 44100      # taxa interna de processamento
        self.output_rate = 11025        # taxa "retrô" final
        self.bit_depth = 4              # bits finais (4 = 16 níveis) -> retro
        self.mu = 255                   # μ para mu-law (quanto maior, mais compressão)
        self.noise_reduction_strength = 0.8  # 0..1 (0 sem redução, 1 forte)
        self.apply_notch = True
        self.notch_freqs = [50, 60]     # freq possíveis de hum (ativa a mais próxima)
        self.hp_cutoff = 40.0           # highpass cutoff para remover subgraves indesejados
        self.spectral_nperseg = 2048    # STFT window size
        self.quantization_levels = 2 ** self.bit_depth

    def load_audio(self):
        self.input_file = filedialog.askopenfilename(
            filetypes=(("Arquivos de Áudio", "*.wav *.mp3 *.ogg *.flac"),)
        )
        if self.input_file and self.status:
            self.status.config(text=f"Carregado: {os.path.basename(self.input_file)}", fg="green")


    def butter_lowpass(self, data, cutoff, fs, order=4):
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = signal.butter(order, normal_cutoff, btype='low')
        return signal.filtfilt(b, a, data)

    def butter_highpass(self, data, cutoff, fs, order=2):
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = signal.butter(order, normal_cutoff, btype='high')
        return signal.filtfilt(b, a, data)

    def apply_notch_filter(self, data, fs, freq, q=30.0):
        # IIR notch
        w0 = freq / (fs / 2)
        b, a = signal.iirnotch(w0, q)
        return signal.filtfilt(b, a, data)

 
    def mu_law_encode(self, x, mu):
        # x: in [-1, 1]
        safe = np.clip(x, -1.0, 1.0)
        return np.sign(safe) * np.log1p(mu * np.abs(safe)) / np.log1p(mu)

    def mu_law_decode(self, y, mu):
        return np.sign(y) * (1.0 / mu) * ((1.0 + mu) ** np.abs(y) - 1.0)

    def spectral_gate(self, samples, fs):
        # STFT
        f, t, Z = signal.stft(samples, fs=fs, nperseg=self.spectral_nperseg)
        magnitude = np.abs(Z)
        phase = np.angle(Z)

        # estimar ruído: frames com menor energia (menor 10%)
        frame_energy = magnitude.mean(axis=0)
        thr_idx = np.argsort(frame_energy)[:max(1, int(0.1 * len(frame_energy)))]
        noise_profile = magnitude[:, thr_idx].mean(axis=1, keepdims=True)

        # Subtrair ruído com força controlada
        cleaned_mag = magnitude - (noise_profile * self.noise_reduction_strength)
        cleaned_mag = np.maximum(cleaned_mag, 0.0)

      
        Z_clean = cleaned_mag * np.exp(1j * phase)
        _, x_rec = signal.istft(Z_clean, fs=fs, nperseg=self.spectral_nperseg)
   
        x_rec = x_rec[:len(samples)]
        return x_rec

    def clean_bitcrush(self, samples, original_rate):
      
        if original_rate != self.internal_rate:
            samples = signal.resample(samples, int(len(samples) * self.internal_rate / original_rate))

        samples = self.butter_highpass(samples, self.hp_cutoff, self.internal_rate, order=2)

        # 3) Se configurado, remover hum (50/60 Hz) usando notch na taxa interna
        if self.apply_notch:
            # escolhe a frequência mais próxima que faz sentido
            for f in self.notch_freqs:
                if f < 0.45 * (self.internal_rate / 2):
                    try:
                        samples = self.apply_notch_filter(samples, self.internal_rate, f, q=30.0)
                    except Exception:
                        pass

        try:
            samples = self.spectral_gate(samples, fs=self.internal_rate)
        except Exception as e:
            logging.warning("Spectral gate falhou, pulando: " + str(e))

        cutoff = 0.45 * self.output_rate
        samples = self.butter_lowpass(samples, cutoff, self.internal_rate, order=4)

     
        output_length = int(len(samples) * self.output_rate / self.internal_rate)
        downsampled = signal.resample(samples, output_length)


        encoded = self.mu_law_encode(downsampled, self.mu)

        levels = self.quantization_levels
        dither = (np.random.random(len(encoded)) - 0.5) * (1.0 / levels) * 0.5
        encoded = encoded + dither

        quantized = np.round(((encoded + 1.0) / 2.0) * (levels - 1)) / (levels - 1)
        quantized = (quantized * 2.0) - 1.0

        decoded = self.mu_law_decode(quantized, self.mu)

        window_size = 3
        smoothed = np.convolve(decoded, np.ones(window_size)/window_size, mode='same')

        return smoothed

    def convert_to_retro(self, show_dialog=False):
        if not self.input_file:
            if self.status:
                self.status.config(text="Selecione um arquivo primeiro!", fg="red")
            return None

        try:
          
            audio = AudioSegment.from_file(self.input_file)
            mono = audio.set_channels(1)
            original = mono.set_frame_rate(self.internal_rate)

            samples = np.array(original.get_array_of_samples(), dtype=np.float32)

            max_val = float(2 ** (8 * original.sample_width - 1))
            samples = samples / max_val
            samples = np.clip(samples, -1.0, 1.0)

       
            processed = self.clean_bitcrush(samples, self.internal_rate)

            processed = np.clip(processed, -0.99, 0.99)

            int8_samples = (processed * 127).astype(np.int8)

            output_segment = AudioSegment(
                data=int8_samples.tobytes(),
                sample_width=1,
                frame_rate=self.output_rate,
                channels=1
            )

            if show_dialog:
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".wav",
                    filetypes=(("Arquivo WAV", "*.wav"),),
                    initialfile=f"clean_retro_{os.path.basename(self.input_file)}"
                )
                if save_path:
                    output_segment.export(save_path, format="wav")
                    if self.status:
                        self.status.config(text=f"Áudio retro limpo salvo!", fg="green")

            return output_segment

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
        """Reprodução direta usando float32 (mais compatível com sounddevice)."""
        try:
            samples = np.array(audio.get_array_of_samples())
            # converter 8-bit signed -> float32
            if audio.sample_width == 1:
                # int8 -> float32
                data = samples.astype(np.float32) / 127.0
            else:
                max_val = float(2 ** (8 * audio.sample_width - 1))
                data = samples.astype(np.float32) / max_val

            samplerate = audio.frame_rate
            sd.play(data, samplerate)
            sd.wait()
        except Exception as e:
            if self.status:
                self.status.config(text=f"Erro na prévia: {str(e)}", fg="red")
            logging.error(f"Erro na reprodução: {str(e)}")

    def save(self):
        self.convert_to_retro(show_dialog=True)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Conversor de Áudio Retro Limpo")
    root.geometry("420x220")

    converter = CleanRetroConverter()

    load_btn = tk.Button(root, text="Carregar Áudio", command=converter.load_audio, width=20, height=2)
    load_btn.pack(pady=10)

    preview_btn = tk.Button(root, text="Preview", command=converter.preview, width=20, height=2)
    preview_btn.pack(pady=5)

    save_btn = tk.Button(root, text="Salvar Áudio", command=converter.save, width=20, height=2)
    save_btn.pack(pady=10)

    converter.status = tk.Label(root, text="Selecione um arquivo de áudio")
    converter.status.pack(pady=10)

    root.mainloop()
